from datetime import datetime
from netaddr import EUI
from django.db.models import Q
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
from djing2.lib.logger import logger
from networks.models import CustomerIpLeaseModel
from radiusapp.vendor_base import AcctStatusType
from radiusapp.vendors import VendorManager
from radiusapp import custom_signals
# from radiusapp.tasks import async_finish_session_task

import logging
fh = logging.FileHandler('/tmp/djing2_s.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


def _gigaword_imp(num: int, gwords: int) -> int:
    num = safe_int(num)
    gwords = safe_int(gwords)
    return num + gwords * (10 ** 9)


def _bad_ret(text, custom_status=status.HTTP_400_BAD_REQUEST):
    logger.error(text)
    return Response({"Reply-Message": text}, status=custom_status)


def _update_lease_send_ws_signal(customer_id: int):
    send_data2ws({
        "eventType": WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value,
        "data": {
            "customer_id": customer_id
        }
    })


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
            return Response({
                "Reply-Message": "Customer service not found"
            }, status=status.HTTP_404_NOT_FOUND)

        sess_time = customer_service.calc_session_time()
        return Response({
            "ip": customer_ip,
            "session_time": int(sess_time.total_seconds()),
            "speed_in": customer_service.service.speed_in,
            "speed_out": customer_service.service.speed_out,
        })

    @get_service.mapping.get
    def get_service_get(self, request, **kwargs):
        serializer = self.get_serializer()
        return Response(serializer.data)

    @action(methods=["post"], detail=False, url_path=r"auth/(?P<vendor_name>\w{1,32})")
    def auth(self, request, vendor_name=None):
        # Just find customer by credentials from request
        vendor_manager = VendorManager(vendor_name=vendor_name)
        self.vendor_manager = vendor_manager

        opt82 = vendor_manager.get_opt82(data=request.data)
        if not opt82:
            return _bad_ret("Failed fetch opt82 info")
        agent_remote_id, agent_circuit_id = opt82

        customer_mac = vendor_manager.get_customer_mac(request.data)
        if not customer_mac:
            return _bad_ret("Customer mac is required")

        customer = None
        subscriber_lease = None

        if all((agent_remote_id, agent_circuit_id)):
            dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
                agent_remote_id=agent_remote_id,
                agent_circuit_id=agent_circuit_id
            )
            if not dev_mac:
                return _bad_ret("Failed to parse option82")

            customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
                device_mac=dev_mac,
                device_port=dev_port
            )
            if customer is None:
                return _bad_ret('Customer not found', custom_status=status.HTTP_404_NOT_FOUND)
            # TODO: Optimize

            # Ищем по сущ сессиям
            subscriber_session = CustomerRadiusSession.objects.filter(
                customer=customer,
                ip_lease__mac_address=customer_mac,
            ).select_related('ip_lease')
            if subscriber_session.exists():
                subscriber_lease = subscriber_session.first().ip_lease
            else:
                subscriber_lease = CustomerIpLeaseModel.objects.filter(
                    Q(mac_address=customer_mac, is_dynamic=True) | Q(is_dynamic=False),
                    customer=customer,
                    # mac_address=customer_mac
                ).first()
        else:
            leases = CustomerIpLeaseModel.objects.filter(
                mac_address=str(customer_mac)
            ).select_related(
                'customer',
                'customer__current_service',
                'customer__current_service__service',
            )
            # TODO: Optimize
            if leases.exists():
                subscriber_lease = leases.first()
                customer = subscriber_lease.customer if subscriber_lease else None
            del leases

        if customer is None:
            return _bad_ret(
                'Customer not found',
                custom_status=status.HTTP_404_NOT_FOUND
            )

        # Return auth response
        try:
            r = vendor_manager.get_auth_session_response(
                customer_service=customer.active_service(),
                customer=customer,
                request_data=request.data,
                subscriber_lease=subscriber_lease,
            )
            if r is None:
                logger.error('Empty auth session response')
                return Response(
                    'Empty auth session response',
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            response, code = r
            _update_lease_send_ws_signal(customer.pk)
            return Response(response, status=code)
        except LogicError as err:
            return _bad_ret(str(err))

    @action(methods=["post"], detail=False, url_path=r"acct/(?P<vendor_name>\w{1,32})")
    def acct(self, request, vendor_name=None):
        if vendor_name is None:
            return _bad_ret('Empty vendor name')

        vendor_manager = VendorManager(vendor_name=vendor_name)
        self.vendor_manager = vendor_manager

        request_type = vendor_manager.get_acct_status_type(request)
        if request_type is None:
            logger.error('request_type is None')
            return self._acct_unknown(request, 'request_type is None')
        acct_status_type_map = {
            AcctStatusType.START.value: self._acct_start,
            AcctStatusType.STOP.value: self._acct_stop,
            AcctStatusType.UPDATE.value: self._acct_update,
        }
        #request_type_fn = acct_status_type_map.get(request_type.value, self._acct_unknown)
        request_type_fn = acct_status_type_map.get(request_type.value)
        if request_type_fn is None:
            err = 'request_type_fn is None, (request_type=%s)' % request_type
            logger.error(err)
            return self._acct_unknown(request, err)
        return request_type_fn(request)

    def _update_counters(self, sessions, data: dict, customer_mac: EUI,
                        last_event_time=None, **update_kwargs):
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
        vendor_manager = self.vendor_manager
        radius_unique_id = vendor_manager.get_radius_unique_id(data)
        ip = vcls.get_rad_val(data, "Framed-IP-Address")
        custom_signals.radius_auth_update_signal.send(
            sender=CustomerRadiusSession,
            instance=None,
            instance_queryset=sessions,
            data=data,
            input_octets=v_in_pkt,
            output_octets=v_out_oct,
            input_packets=v_in_pkt,
            output_packets=v_out_pkt,
            radius_unique_id=radius_unique_id,
            ip_addr=ip,
            customer_mac=customer_mac
        )

    def _acct_start(self, request):
        """Accounting start handler."""
        vendor_manager = self.vendor_manager
        if not vendor_manager or not vendor_manager.vendor_class:
            return _bad_ret(
                'No vendor manager exists',
                custom_status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        dat = request.data
        if not dat:
            return _bad_ret("Empty request")

        ip = vendor_manager.vendor_class.get_rad_val(dat, "Framed-IP-Address")
        if not ip:
            return _bad_ret(
                "Request has no ip information (Framed-IP-Address)",
                custom_status=status.HTTP_200_OK
            )

        radius_username = vendor_manager.get_radius_username(dat)
        if not radius_username:
            return _bad_ret(
                "Request has no username",
                custom_status=status.HTTP_200_OK
            )

        opt82 = vendor_manager.get_opt82(data=request.data)
        if opt82 is None:
            return _bad_ret('Bad opt82')

        agent_remote_id, agent_circuit_id = opt82
        if all([agent_remote_id, agent_circuit_id]):
            dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
                agent_remote_id=agent_remote_id, agent_circuit_id=agent_circuit_id
            )
            if not dev_mac:
                return _bad_ret('bad opt82 device mac address')
            customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
                device_mac=dev_mac,
                device_port=dev_port
            )
            if not customer:
                return _bad_ret(
                    'Customer with provided device credentials not found: %s _ %s' % (str(dev_mac), str(dev_port)),
                    custom_status=status.HTTP_404_NOT_FOUND
                )
        else:
            return _bad_ret(
                    "Request has not opt82 info: %s" % (opt82),
                custom_status=status.HTTP_200_OK
            )

        radius_unique_id = vendor_manager.get_radius_unique_id(dat)
        customer_mac = vendor_manager.get_customer_mac(dat)

        created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
            ip=str(ip),
            mac=str(customer_mac),
            customer_id=customer.pk,
            radius_uname=radius_username,
            radius_unique_id=radius_unique_id
        )

        if created:
            custom_signals.radius_acct_start_signal.send(
                sender=CustomerRadiusSession,
                instance=None,
                data=dat,
                ip_addr=ip,
                customer_mac=customer_mac,
                radius_username=radius_username,
                customer_ip_lease=None,
                customer=customer,
                radius_unique_id=radius_unique_id,
                event_time=datetime.now(),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_stop(self, request):
        dat = request.data
        vendor_manager = self.vendor_manager
        vcls = vendor_manager.vendor_class
        ip = vcls.get_rad_val(dat, "Framed-IP-Address")
        radius_unique_id = vendor_manager.get_radius_unique_id(dat)
        customer_mac = vendor_manager.get_customer_mac(dat)
        sessions = CustomerRadiusSession.objects.filter(ip_lease__ip_address=ip)
        custom_signals.radius_acct_stop_signal.send(
            sender=CustomerRadiusSession,
            instance_queryset=sessions,
            data=dat,
            ip_addr=ip,
            radius_unique_id=radius_unique_id,
            customer_mac=customer_mac,
        )
        #for session in sessions:
        #    async_finish_session_task(
        #        radius_uname=str(session.radius_username)
        #    )
        sessions.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _acct_update(self, request):
        dat = request.data
        vendor_manager = self.vendor_manager
        vendor_manager_class = vendor_manager.vendor_class
        ip = vendor_manager_class.get_rad_val(dat, "Framed-IP-Address")
        sessions = CustomerRadiusSession.objects.filter(
            ip_lease__ip_address=ip,
        )
        customer_mac = vendor_manager.get_customer_mac(dat)
        event_time = datetime.now()
        self._update_counters(
            sessions=sessions,
            data=dat,
            last_event_time=event_time,
            customer_mac=customer_mac
        )
        #CustomerIpLeaseModel.objects.filter(ip_address=ip).update(
        #    last_update=event_time,
        #    mac_address=customer_mac
        #)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _acct_unknown(_, tx=''):
        logger.error('Unknown acct: %s' % tx)
        return _bad_ret("Bad Acct-Status-Type: %s" % tx, custom_status=status.HTTP_200_OK)
