from typing import Optional
from datetime import datetime

from django.db.utils import IntegrityError
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
from radiusapp.tasks import async_finish_session_task
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

    @action(methods=["post"], detail=False)
    def get_service(self, request):
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

    @get_service.mapping.get
    def get_service_get(self, request, **kwargs):
        serializer = self.get_serializer()
        return Response(serializer.data)

    def assign_guest(self, customer_mac: str, data: dict, customer_id: Optional[int] = None):
        """
        Assign no service session.

        :param customer_mac: Customer device MAC address.
        :param data: Other data from RADIUS server.
        :param customer_id: customers.models.Customer model id.
        :return: rest_framework Response.
        """
        if customer_id is None:
            lease = CustomerRadiusSession.objects.assign_guest_session(customer_mac=customer_mac)
        else:
            customer_id = safe_int(customer_id)
            if customer_id == 0:
                return _bad_ret('Bad "customer_id" arg.')
            lease = CustomerRadiusSession.objects.assign_guest_customer_session(
                customer_id=customer_id, customer_mac=customer_mac
            )
        if lease is None:
            # Not possible to assign guest ip, it's bad
            return Response(
                {"Reply-Message": "Not possible to assign guest ip, it's bad"},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Creating guest session
        r = self.vendor_manager.get_auth_guest_session_response(guest_lease=lease, data=data)
        return Response(r)

    @action(methods=["post"], detail=False, url_path=r"auth/(?P<vendor_name>\w{1,32})")
    def auth(self, request, vendor_name=None):
        vendor_manager = VendorManager(vendor_name=vendor_name)
        self.vendor_manager = vendor_manager

        agent_remote_id, agent_circuit_id = vendor_manager.get_opt82(data=request.data)

        customer_mac = vendor_manager.get_customer_mac(request.data)
        if customer_mac is None:
            return _bad_ret("Customer mac is required")

        customer = None

        if all([agent_remote_id, agent_circuit_id]):
            dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
                agent_remote_id=agent_remote_id, agent_circuit_id=agent_circuit_id
            )
            if dev_mac is None:
                return _bad_ret("Failed to parse option82")

            customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
                device_mac=dev_mac, device_port=dev_port
            )
        else:
            # return _bad_ret("Bad opt82")
            leases = CustomerIpLeaseModel.objects.filter(mac_address=customer_mac)
            if leases.exists():
                lease = leases.first()
                customer = lease.customer if lease else None
            del leases

        if customer is None:
            # If customer not found then assign guest session
            return self.assign_guest(customer_mac=customer_mac, data=request.data)

        # radius_username = vendor_manager.get_radius_username(request.data)
        # radius_unique_id = vendor_manager.get_radius_unique_id(request.data)

        if customer.current_service_id is None:
            # if customer has not service then assign guest
            #  session with attached customer.
            r = self.assign_guest(
                customer_mac=customer_mac,
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
            r = self.assign_guest(
                customer_mac=customer_mac,
                data=request.data,
                customer_id=customer.pk,
            )
            _update_lease_send_ws_signal(customer.pk)
            return r

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
                r = self.assign_guest(
                    customer_mac=customer_mac,
                    data=request.data,
                    customer_id=customer.pk,
                )
                _update_lease_send_ws_signal(customer.pk)
                return r

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

    def _update_counters(self, sessions, data: dict, **update_kwargs):
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
        return sessions.update(
            last_event_time=datetime.now(),
            input_octets=v_inp_oct,
            output_octets=v_out_oct,
            input_packets=v_in_pkt,
            output_packets=v_out_pkt,
            **update_kwargs,
        )

    def _acct_start(self, request):
        """Accounting start handler."""
        dat = request.data
        vendor_manager = self.vendor_manager

        ip = vendor_manager.vendor_class.get_rad_val(dat, "Framed-IP-Address")
        if not ip:
            return Response(status=status.HTTP_204_NO_CONTENT)

        radius_username = vendor_manager.get_radius_username(dat)
        if not radius_username:
            return Response(status=status.HTTP_204_NO_CONTENT)

        leases = CustomerIpLeaseModel.objects.filter(ip_address=ip).only("pk", "ip_address", "pool_id", "customer_id")
        if not leases.exists():
            return Response(status=status.HTTP_204_NO_CONTENT)

        lease = leases.first()
        if lease is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        radius_unique_id = vendor_manager.get_radius_unique_id(dat)

        sessions = CustomerRadiusSession.objects.filter(ip_lease=lease)
        if sessions.exists():
            sessions.update(customer=lease.customer, radius_username=radius_username, session_id=radius_unique_id)
            return Response(status=status.HTTP_204_NO_CONTENT)

        try:
            CustomerRadiusSession.objects.create(
                customer=lease.customer,
                ip_lease=lease,
                last_event_time=datetime.now(),
                radius_username=radius_username,
                session_id=radius_unique_id,
            )
        except IntegrityError:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_stop(self, request):
        dat = request.data
        vendor_manager = self.vendor_manager
        vcls = vendor_manager.vendor_class
        ip = vcls.get_rad_val(dat, "Framed-IP-Address")
        CustomerIpLeaseModel.objects.filter(ip_address=ip).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_update(self, request):
        dat = request.data
        vendor_manager = self.vendor_manager
        vcls = vendor_manager.vendor_class
        ip = vcls.get_rad_val(dat, "Framed-IP-Address")
        sessions = CustomerRadiusSession.objects.filter(
            ip_lease__ip_address=ip,
        )
        if sessions.exists():
            self._update_counters(sessions=sessions, data=dat)

            radius_username = vendor_manager.get_radius_username(dat)

            for single_session in sessions.iterator():
                single_customer = single_session.customer

                # If session and customer not same then free session
                agent_remote_id, agent_circuit_id = vendor_manager.get_opt82(data=dat)
                if all([agent_remote_id, agent_circuit_id]):
                    dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
                        agent_remote_id=agent_remote_id, agent_circuit_id=agent_circuit_id
                    )
                    if dev_mac is not None:
                        customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
                            device_mac=dev_mac, device_port=dev_port
                        )
                        if customer.pk != single_session.customer_id:
                            async_finish_session_task(radius_uname=radius_username)
                            return

                # If customer access state and session type not equal
                if single_session.is_inet_session() != single_customer.is_access():
                    # then send disconnect
                    async_finish_session_task(radius_uname=radius_username)
        else:
            return _bad_ret("No session found")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _acct_unknown(_):
        return _bad_ret("Bad Acct-Status-Type")
