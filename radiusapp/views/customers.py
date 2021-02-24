from datetime import datetime
from typing import Optional, Union

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from customers.models import CustomerService
from customers.serializers import RadiusCustomerServiceRequestSerializer
from djing2.lib import LogicError, safe_int
from djing2.viewsets import DjingAuthorizedViewSet
from networks.models import NetworkIpPoolKind, CustomerIpLeaseModel
from radiusapp.models import CustomerRadiusSession
from radiusapp.vendors import VendorManager


def _get_acct_rad_val(data, v, default=None) -> Optional[Union[str, int]]:
    attr = data.get(v)
    if isinstance(attr, (list, tuple)):
        return attr[0]
    if attr:
        return attr
    return default


def _gigaword_imp(num: int, gwords: int) -> int:
    num = safe_int(num)
    gwords = safe_int(gwords)
    return num + gwords * (10 ** 9)


def _bad_ret(text):
    return Response({
        'Reply-Message': text
    }, status=status.HTTP_403_FORBIDDEN)


class RadiusCustomerServiceRequestViewSet(DjingAuthorizedViewSet):
    serializer_class = RadiusCustomerServiceRequestSerializer
    vendor_manager = None

    def _check_data(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.serializer = serializer
        return serializer.data

    @action(methods=['get', 'post'], detail=False)
    def get_service(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer()
            return Response(serializer.data)
        data = self._check_data(request.data)

        customer_ip = data.get('customer_ip')
        # password = data.get('password')

        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr=customer_ip
        )
        if customer_service is None:
            return Response({
                'Reply-Message': 'Customer service not found'
            }, status=status.HTTP_404_NOT_FOUND)

        sess_time = customer_service.calc_session_time()
        return Response({
            'ip': customer_ip,
            'session_time': int(sess_time.total_seconds()),
            'speed_in': customer_service.service.speed_in,
            'speed_out': customer_service.service.speed_out
        })

    def assign_guest_session(self, radius_uname: str, customer_mac: str, session_id: str, data):
        guest_session = CustomerRadiusSession.objects.assign_guest_session(
            radius_uname=radius_uname,
            customer_mac=customer_mac,
            session_id=session_id
        )
        if guest_session is None:
            # Not possible to assign guest ip, it's bad
            return Response({
                'Reply-Message': "Not possible to assign guest ip, it's bad"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Creating guest session
        r = self.vendor_manager.get_auth_guest_session_response(
            guest_session=guest_session,
            data=data
        )
        return Response(r)

    @action(methods=['post'], detail=False, url_path='auth/(?P<vendor_name>\w{1,32})')
    def auth(self, request, vendor_name=None):
        vendor_manager = VendorManager(vendor_name=vendor_name)
        self.vendor_manager = vendor_manager

        agent_remote_id, agent_circuit_id = vendor_manager.get_opt82(
            data=request.data
        )

        if not all([agent_remote_id, agent_circuit_id]):
            return _bad_ret('Bad opt82')

        dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
            agent_remote_id=agent_remote_id,
            agent_circuit_id=agent_circuit_id
        )

        if dev_mac is None:
            return _bad_ret('Failed to parse option82')

        customer_mac = vendor_manager.get_customer_mac(request.data)
        if customer_mac is None:
            return _bad_ret('Customer mac is required')

        radius_username = vendor_manager.get_radius_username(request.data)
        radius_unique_id = vendor_manager.get_radius_unique_id(request.data)

        customer = CustomerIpLeaseModel.find_customer_by_device_credentials(
            device_mac=dev_mac,
            device_port=dev_port
        )
        if customer is None:
            return self.assign_guest_session(
                radius_uname=radius_username,
                customer_mac=customer_mac,
                session_id=radius_unique_id,
                data=request.data
            )

        customer_service = CustomerService.find_customer_service_by_device_credentials(
            customer_id=customer.pk,
            current_service_id=customer.current_service_id
        )
        if customer_service is None:
            return self.assign_guest_session(
                radius_uname=radius_username,
                customer_mac=customer_mac,
                session_id=radius_unique_id,
                data=request.data
            )

        # sess_time = customer_service.calc_session_time()

        vid = vendor_manager.get_vlan_id(request.data)

        try:
            subscriber_lease = CustomerRadiusSession.objects.fetch_subscriber_lease(
                customer_mac=customer_mac,
                customer_id=customer.pk,
                customer_group=customer.group_id,
                is_dynamic=True,
                vid=vid,
                pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET
            )
            if subscriber_lease is None:
                return self.assign_guest_session(
                    radius_uname=radius_username,
                    customer_mac=customer_mac,
                    session_id=radius_unique_id,
                    data=request.data
                )

            # create authorized session for customer
            CustomerRadiusSession.objects.create(
                customer_id=customer.pk,
                last_event_time=datetime.now(),
                radius_username=radius_username,
                ip_lease_id=subscriber_lease.lease_id,
                session_id=radius_unique_id
            )

            response = vendor_manager.get_auth_session_response(
                subscriber_lease=subscriber_lease,
                customer_service=customer_service,
                customer=customer,
                request_data=request.data
            )
            return Response(response)
        except LogicError as err:
            return _bad_ret(str(err))

    @action(methods=['post'], detail=False)
    def acct(self, request):
        # return Response(status=status.HTTP_201_CREATED)

        # FIXME: Pass name to 'vendor_name' from request
        # vendor_manager = VendorManager(vendor_name='juniper')

        # dat = request.data

        # is_stop_radius_session = False
        # act_type = _get_acct_rad_val(dat, 'Acct-Status-Type')
        # if act_type not in ['Start', 'Stop', 'Interim-Update', 'Accounting-On']:
        #     return _bad_ret('Bad Acct-Status-Type')
        # if act_type == 'Stop':
        #     is_stop_radius_session = True

        # customer_mac = vendor_manager.get_customer_mac(request.data)
        # if customer_mac is None:
        #     return _bad_ret('Customer mac is required')

        # ip = _get_acct_rad_val(dat, 'Framed-IP-Address')
        # if ip is None:
        #     return _bad_ret('Framed-IP-Address required')

        # agent_remote_id, agent_circuit_id = vendor_manager.get_opt82(
        #     data=request.data
        # )
        #
        # if not all([agent_remote_id, agent_circuit_id]):
        #     return _bad_ret('Bad opt82')

        # dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
        #     agent_remote_id=agent_remote_id,
        #     agent_circuit_id=agent_circuit_id
        # )

        # radius_username = _get_acct_rad_val(dat, 'User-Name')

        # create or update radius session
        # CustomerRadiusSession.objects.create_or_update_session(
        #     session_id=_get_acct_rad_val(dat, 'Acct-Unique-Session-Id'),
        #     lease_id=,
        #     v_dev_mac=dev_mac,
        #     v_dev_port=dev_port,
        #     v_sess_time=timedelta(seconds=safe_int(_get_acct_rad_val(dat, 'Acct-Session-Time', 0))),
        #     v_uname=radius_username,
        #     v_inp_oct=_gigaword_imp(
        #         num=_get_acct_rad_val(dat, 'Acct-Input-Octets', 0),
        #         gwords=_get_acct_rad_val(dat, 'Acct-Input-Gigawords', 0)
        #     ),
        #     v_out_oct=_gigaword_imp(
        #         num=_get_acct_rad_val(dat, 'Acct-Output-Octets', 0),
        #         gwords=_get_acct_rad_val(dat, 'Acct-Output-Gigawords', 0)
        #     ),
        #     v_in_pkt=_get_acct_rad_val(dat, 'Acct-Input-Packets', 0),
        #     v_out_pkt=_get_acct_rad_val(dat, 'Acct-Output-Packets', 0),
        #     v_is_stop=is_stop_radius_session
        # )

        # update ip addr in customer profile
        # try:
        #     res_text = CustomerIpLeaseModel.lease_commit_add_update(
        #         client_ip=ip,
        #         mac_addr=mac,
        #         dev_mac=dev_mac,
        #         dev_port=dev_port
        #     )
        # except LogicError as err:
        #     res_text = str(err)
        # if res_text is not None:
        #     res_text = {
        #         'Reply-Message': res_text
        #     }
        # else:
        #     res_text = None
        return Response(status=status.HTTP_201_CREATED)
        # return Response(res_text, status=status.HTTP_204_NO_CONTENT if res_text is None else status.HTTP_200_OK)
        # is_access = CustomerIpLeaseModel.objects.get_service_permit_by_ip()
        # access_status = status.HTTP_200_OK if is_access else status.HTTP_403_FORBIDDEN
        # return Response(status=access_status)
        # return Response({
        #     'Acct-Interim-Interval': 300,
        #     # 'Mikrotik-Address-List': 'DjingUsersAllowed',
        #     'Mikrotik-Rate-Limit': '50M/43M'
        # })
