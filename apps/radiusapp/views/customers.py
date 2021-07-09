from typing import Optional
from datetime import datetime
from netaddr import EUI
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import AllowAny

from customers.models import CustomerService
from customers.serializers import RadiusCustomerServiceRequestSerializer
from djing2.lib import LogicError, safe_int
from djing2.lib.ws_connector import WsEventTypeEnum, send_data2ws
from djing2.lib.mixins import AllowedSubnetMixin
from networks.models import NetworkIpPoolKind, CustomerIpLeaseModel
from radiusapp.models import CustomerRadiusSession
from radiusapp.vendor_base import AcctStatusType
from radiusapp.vendors import VendorManager
from radiusapp import custom_signals
from radiusapp import tasks


def _gigaword_imp(num: int, gwords: int) -> int:
    num = safe_int(num)
    gwords = safe_int(gwords)
    return num + gwords * (10 ** 9)


def _bad_ret(text, custom_status=status.HTTP_400_BAD_REQUEST):
    return Response({"Reply-Message": text}, status=custom_status)


def _update_lease_send_ws_signal(customer_id: int):
    send_data2ws({"eventType": WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value, "data": {"customer_id": customer_id}})


# TODO: Also protect requests by hash
class RadiusCustomerServiceRequestViewSet(AllowedSubnetMixin, GenericViewSet):
    serializer_class = RadiusCustomerServiceRequestSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
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

    def assign_guest(self, customer_mac: EUI, data: dict, customer_id: Optional[int] = None):
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
        if not customer_mac:
            return _bad_ret("Customer mac is required")

        customer = None

        if all([agent_remote_id, agent_circuit_id]):
            dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
                agent_remote_id=agent_remote_id, agent_circuit_id=agent_circuit_id
            )
            if not dev_mac:
                return _bad_ret("Failed to parse option82")

            customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
                device_mac=dev_mac, device_port=dev_port
            )
        else:
            # return _bad_ret("Bad opt82")
            leases = CustomerIpLeaseModel.objects.filter(mac_address=str(customer_mac))
            if leases.exists():
                lease = leases.first()
                customer = lease.customer if lease else None
            del leases

        if customer is None:
            # If customer not found then assign guest session
            return self.assign_guest(customer_mac=customer_mac, data=request.data)

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
                # TODO: customer.active_service() - hit to db
                customer_service=customer.active_service(),
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

    def _update_counters(self, sessions, data: dict, last_event_time=None, **update_kwargs):
        if last_event_time is None:
            last_event_time = datetime.now()
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
        sessions.update(
            last_event_time=last_event_time,
            input_octets=v_inp_oct,
            output_octets=v_out_oct,
            input_packets=v_in_pkt,
            output_packets=v_out_pkt,
            **update_kwargs,
        )
        custom_signals.radius_auth_update_signal.send(
            sender=CustomerRadiusSession,
            instance=None,
            instance_queryset=sessions,
            data=data,
            input_octets=v_in_pkt,
            output_octets=v_out_oct,
            input_packets=v_in_pkt,
            output_packets=v_out_pkt,
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
            self._update_counters(
                sessions=sessions,
                data=dat,
                customer=lease.customer,
                radius_username=radius_username,
                session_id=radius_unique_id,
                last_event_time=datetime.now(),
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        try:
            customer = lease.customer
            event_time = datetime.now()
            new_session = CustomerRadiusSession.objects.create(
                customer=customer,
                ip_lease=lease,
                last_event_time=event_time,
                radius_username=radius_username,
                session_id=radius_unique_id,
            )
            customer_mac = vendor_manager.get_customer_mac(dat)
            custom_signals.radius_auth_start_signal.send(
                sender=CustomerRadiusSession,
                instance=new_session,
                data=dat,
                ip_addr=ip,
                customer_mac=customer_mac,
                radius_username=radius_username,
                customer_ip_lease=lease,
                customer=customer,
                radius_unique_id=radius_unique_id,
                event_time=event_time,
            )
        except IntegrityError:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_stop(self, request):
        # TODO: Удалять только сессию, без ip, только при Accounting-Stop.
        #  Получается, что когда сессия останавливается из radius, то и из билинга она пропадает.
        #  Но только сессия, ip удалять не надо.
        dat = request.data
        vendor_manager = self.vendor_manager
        vcls = vendor_manager.vendor_class
        ip = vcls.get_rad_val(dat, "Framed-IP-Address")
        radius_unique_id = vendor_manager.get_radius_unique_id(dat)
        customer_mac = vendor_manager.get_customer_mac(dat)
        sessions = CustomerRadiusSession.objects.filter(ip_lease__ip_address=ip)
        custom_signals.radius_auth_stop_signal.send(
            sender=CustomerRadiusSession,
            instance_queryset=sessions,
            data=dat,
            ip_addr=ip,
            radius_unique_id=radius_unique_id,
            customer_mac=customer_mac,
        )
        sessions.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_update(self, request):
        dat = request.data
        vendor_manager = self.vendor_manager
        vcls = vendor_manager.vendor_class
        ip = vcls.get_rad_val(dat, "Framed-IP-Address")
        sessions = CustomerRadiusSession.objects.filter(
            ip_lease__ip_address=ip,
        )
        event_time = datetime.now()
        CustomerIpLeaseModel.objects.filter(ip_address=ip).update(last_update=event_time)
        if sessions.exists():
            self._update_counters(sessions=sessions, data=dat)

            for single_session in sessions.iterator():
                # single_customer = single_session.customer

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
                        if (
                            customer is not None
                            and single_session.customer_id is not None
                            and int(customer.pk) != int(single_session.customer_id)
                        ):
                            tasks.async_finish_session_task(radius_uname=single_session.radius_username)
                            single_session.delete()
                            return Response(status=status.HTTP_204_NO_CONTENT)

        else:
            radius_username = vendor_manager.get_radius_username(dat)
            if radius_username:
                tasks.async_finish_session_task(radius_uname=radius_username)
            return _bad_ret("No session found", custom_status=status.HTTP_200_OK)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _acct_unknown(_):
        return _bad_ret("Bad Acct-Status-Type")
