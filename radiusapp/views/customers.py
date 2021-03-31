from typing import Optional
from datetime import datetime

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from customers.models import CustomerService
from customers.serializers import RadiusCustomerServiceRequestSerializer
from djing2.lib import LogicError, safe_int
from djing2.lib.ws_connector import WsEventTypeEnum, send_data2ws
from djing2.viewsets import DjingAuthorizedViewSet
from networks.models import NetworkIpPoolKind, CustomerIpLeaseModel
from radiusapp.models import CustomerRadiusSession
from radiusapp.vendor_base import AcctStatusType
from radiusapp.vendors import VendorManager


def _gigaword_imp(num: int, gwords: int) -> int:
    num = safe_int(num)
    gwords = safe_int(gwords)
    return num + gwords * (10 ** 9)


def _bad_ret(text):
    return Response({"Reply-Message": text}, status=status.HTTP_400_BAD_REQUEST)


def _update_lease_send_ws_signal(customer_id: int):
    send_data2ws({"eventType": WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value, "data": {"customer_id": customer_id}})


class RadiusCustomerServiceRequestViewSet(DjingAuthorizedViewSet):
    serializer_class = RadiusCustomerServiceRequestSerializer
    vendor_manager = None

    def _check_data(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.serializer = serializer
        return serializer.data

    @action(methods=["get", "post"], detail=False)
    def get_service(self, request):
        if request.method == "GET":
            serializer = self.get_serializer()
            return Response(serializer.data)
        data = self._check_data(request.data)

        customer_ip = data.get("customer_ip")
        # password = data.get('password')

        customer_service = CustomerService.get_user_credentials_by_ip(ip_addr=customer_ip)
        if customer_service is None:
            return Response({"Reply-Message": "Customer service not found"}, status=status.HTTP_404_NOT_FOUND)

        sess_time = customer_service.calc_session_time()
        return Response(
            {
                "ip": customer_ip,
                "session_time": int(sess_time.total_seconds()),
                "speed_in": customer_service.service.speed_in,
                "speed_out": customer_service.service.speed_out,
            }
        )

    def assign_guest_session(
        self, radius_uname: str, customer_mac: str, session_id: str, data: dict, customer_id: Optional[int] = None
    ):
        """
        Assign no service session.

        :param radius_uname: User-Name av value from RADIUS.
        :param customer_mac: Customer device MAC address.
        :param session_id: RADIUS unique id.
        :param data: Other data from RADIUS server.
        :param customer_id: customers.models.Customer model id.
        :return: rest_framework Response.
        """
        if customer_id is None:
            session = CustomerRadiusSession.objects.assign_guest_session(
                radius_uname=radius_uname, customer_mac=customer_mac, session_id=session_id
            )
        else:
            customer_id = safe_int(customer_id)
            if customer_id == 0:
                return _bad_ret('Bad "customer_id" arg.')
            session = CustomerRadiusSession.objects.assign_guest_customer_session(
                radius_uname=radius_uname, customer_id=customer_id, customer_mac=customer_mac, session_id=session_id
            )
        if session is None:
            # Not possible to assign guest ip, it's bad
            return Response(
                {"Reply-Message": "Not possible to assign guest ip, it's bad"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        # Creating guest session
        r = self.vendor_manager.get_auth_guest_session_response(guest_session=session, data=data)
        return Response(r)

    @action(methods=["post"], detail=False, url_path=r"auth/(?P<vendor_name>\w{1,32})")
    def auth(self, request, vendor_name=None):
        vendor_manager = VendorManager(vendor_name=vendor_name)
        self.vendor_manager = vendor_manager

        agent_remote_id, agent_circuit_id = vendor_manager.get_opt82(data=request.data)

        if not all([agent_remote_id, agent_circuit_id]):
            return _bad_ret("Bad opt82")

        dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
            agent_remote_id=agent_remote_id, agent_circuit_id=agent_circuit_id
        )

        if dev_mac is None:
            return _bad_ret("Failed to parse option82")

        customer_mac = vendor_manager.get_customer_mac(request.data)
        if customer_mac is None:
            return _bad_ret("Customer mac is required")

        radius_username = vendor_manager.get_radius_username(request.data)
        radius_unique_id = vendor_manager.get_radius_unique_id(request.data)

        customer = CustomerIpLeaseModel.find_customer_by_device_credentials(device_mac=dev_mac, device_port=dev_port)
        if customer is None:
            # If customer not found then assign guest session
            return self.assign_guest_session(
                radius_uname=radius_username, customer_mac=customer_mac, session_id=radius_unique_id, data=request.data
            )

        if customer.current_service_id is None:
            # if customer has not service then assign guest
            #  session with attached customer.
            r = self.assign_guest_session(
                radius_uname=radius_username,
                customer_mac=customer_mac,
                session_id=radius_unique_id,
                data=request.data,
                customer_id=customer.pk,
            )
            _update_lease_send_ws_signal(customer.pk)
            return r

        customer_service = CustomerService.find_customer_service_by_device_credentials(
            customer_id=customer.pk, current_service_id=int(customer.current_service_id)
        )
        if customer_service is None:
            # if customer has not service then assign guest
            #  session with attached customer.
            r = self.assign_guest_session(
                radius_uname=radius_username,
                customer_mac=customer_mac,
                session_id=radius_unique_id,
                data=request.data,
                customer_id=customer.pk,
            )
            _update_lease_send_ws_signal(customer.pk)
            return r

        # TODO: return time to end session.
        # sess_time = customer_service.calc_session_time()

        vid = vendor_manager.get_vlan_id(request.data)

        try:
            subscriber_lease = CustomerRadiusSession.objects.fetch_subscriber_lease(
                customer_mac=customer_mac,
                customer_id=customer.pk,
                customer_group=customer.group_id,
                is_dynamic=True,
                vid=vid,
                pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            )
            if subscriber_lease is None:
                r = self.assign_guest_session(
                    radius_uname=radius_username,
                    customer_mac=customer_mac,
                    session_id=radius_unique_id,
                    data=request.data,
                    customer_id=customer.pk,
                )
                _update_lease_send_ws_signal(customer.pk)
                return r

            # create authorized session for customer
            CustomerRadiusSession.objects.get_or_create(
                ip_lease_id=subscriber_lease.lease_id,
                customer_id=customer.pk,
                defaults={
                    "last_event_time": datetime.now(),
                    "radius_username": radius_username,
                    "session_id": radius_unique_id,
                },
            )

            response = vendor_manager.get_auth_session_response(
                subscriber_lease=subscriber_lease,
                customer_service=customer_service,
                customer=customer,
                request_data=request.data,
            )
            _update_lease_send_ws_signal(customer.pk)
            return Response(response)
        except LogicError as err:
            return _bad_ret(str(err))

    @action(methods=["post"], detail=False, url_path=r"acct/(?P<vendor_name>\w{1,32})")
    def acct(self, request, vendor_name=None):
        vendor_manager = VendorManager(vendor_name=vendor_name)
        self.vendor_manager = vendor_manager

        request_type = vendor_manager.get_acct_status_type(request)
        acct_status_type_map = {
            AcctStatusType.START.value: self._acct_start,
            AcctStatusType.STOP.value: self._acct_stop,
            AcctStatusType.UPDATE.value: self._acct_update,
        }
        request_type_fn = acct_status_type_map.get(request_type.value, self._acct_unknown)
        return request_type_fn(request)

    def _update_counters(self, session, data: dict, **update_kwargs):
        vcls = self.vendor_manager.vendor_class
        v_inp_oct = _gigaword_imp(
            num=vcls.get_rad_val(data, "Acct-Input-Octets", 0),
            gwords=vcls.get_rad_val(data, "Acct-Input-Gigawords", 0),
        )
        v_out_oct = _gigaword_imp(
            num=vcls.get_rad_val(data, "Acct-Output-Octets", 0),
            gwords=vcls.get_rad_val(data, "Acct-Output-Gigawords", 0),
        )
        v_in_pkt = vcls.get_rad_val(data, "Acct-Input-Packets", 0)
        v_out_pkt = vcls.get_rad_val(data, "Acct-Output-Packets", 0)
        return session.update(
            last_event_time=datetime.now(),
            input_octets=v_inp_oct,
            output_octets=v_out_oct,
            input_packets=v_in_pkt,
            output_packets=v_out_pkt,
            **update_kwargs,
        )

    # TODO: Сделать создание сессии в acct, а в
    #  auth только предлагать ip для абонента
    @staticmethod
    def _acct_start(_):
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_stop(self, request):
        dat = request.data
        vendor_manager = self.vendor_manager
        username = vendor_manager.get_radius_username(dat)
        vcls = vendor_manager.vendor_class
        ip = vcls.get_rad_val(dat, "Framed-IP-Address")
        session = CustomerRadiusSession.objects.filter(radius_username=username, ip_lease__ip_address=ip, closed=False)
        if not session.exists():
            return Response(status=status.HTTP_204_NO_CONTENT)
        self._update_counters(session, dat, closed=True)
        session = session.first()
        if session is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        customer = session.customer
        if customer.is_access():
            return Response(status=status.HTTP_204_NO_CONTENT)

        # if not access to service
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_update(self, request):
        dat = request.data
        vendor_manager = self.vendor_manager
        vcls = vendor_manager.vendor_class
        username = vendor_manager.get_radius_username(dat)
        ip = vcls.get_rad_val(dat, "Framed-IP-Address")
        session = CustomerRadiusSession.objects.filter(
            radius_username=username,
            ip_lease__ip_address=ip,
            # closed=False
        )
        if session.exists():
            self._update_counters(session, dat)
        session = session.first()
        if session is None:
            return _bad_ret("No session found")

        # if not access to service
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _acct_unknown(_):
        return _bad_ret("Bad Acct-Status-Type")
