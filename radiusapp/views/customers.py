from datetime import timedelta
from typing import Optional, Union

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from customers.models import CustomerService
from customers.serializers import RadiusCustomerServiceRequestSerializer
from djing2.lib import LogicError, safe_int
from djing2.viewsets import DjingAuthorizedViewSet
# from networks.models import CustomerIpLeaseModel
from radiusapp.models import UserSession
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

    @action(methods=['post'], detail=False)
    def auth(self, request):
        # FIXME: Pass name to 'vendor_name' from request
        vendor_manager = VendorManager(vendor_name='juniper')

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

        customer_service = CustomerService.find_customer_service_by_device_credentials(
            dev_mac=dev_mac,
            dev_port=dev_port
        )
        if customer_service is None:
            # user can't access to service
            # return Response(status=status.HTTP_204_NO_CONTENT)
            return Response({
                'Framed-IP-Address': '10.255.0.11',
                'Acct-Interim-Interval': 600,
                'ERX-Service-Activate:1': "SERVICE-INET(100000000,12500000,100000000,12500000)"
            })
        service = customer_service.service

        sin, sout = int(service.speed_in * 1000000), int(service.speed_out * 1000000)
        # sess_time = customer_service.calc_session_time()

        vid = vendor_manager.get_vlan_id(request.data)

        try:
            # TODO: UserSession нужно запоминать
            r = UserSession.objects.fetch_subscriber_lease(
                customer_mac=customer_mac,
                device_mac=dev_mac,
                device_port=dev_port,
                is_dynamic=True,
                vid=vid
            )
            if r is None:
                return Response({
                    'Framed-IP-Address': '10.255.0.102',
                    'Acct-Interim-Interval': 600,
                    'ERX-Service-Activate:1': "SERVICE-INET(100000000,12500000,100000000,12500000)"
                })
            return Response({
                'Framed-IP-Address': r.get('ip_addr'),
                # 'Framed-IP-Netmask': '255.255.0.0',
                'ERX-Service-Activate': f'SERVICE-INET({sin},{int(sin / 8 * 1.5)},{sout},{int(sout / 8 * 1.5)})',
                # 'ERX-Primary-Dns': '10.12.1.9'
                # 'Acct-Interim-Interval': sess_time.total_seconds()
            })
        except LogicError as err:
            return _bad_ret(str(err))

        # return Response({
        #     'Mikrotik-Rate-Limit': speed,
        #     'Mikrotik-Address-List': 'DjingUsersAllowed',
        #     'Session-Timeout': sess_time.total_seconds()
        # })
        # r = {
        #     'User-Name': {'type': 'string', 'value': ['F8:75:A4:AA:C9:E0']},
        #     'User-Password': {'type': 'string', 'value': ['']},
        #     'NAS-IP-Address': {'type': 'ipaddr', 'value': ['10.12.2.10']},
        #     'NAS-Port': {'type': 'integer', 'value': [2212495516]},
        #     'Service-Type': {'type': 'integer', 'value': [2]},
        #     'Framed-IP-Address': {'type': 'ipaddr', 'value': ['192.168.3.50']},
        #     'Called-Station-Id': {'type': 'string', 'value': ['mypool']},
        #     'Calling-Station-Id': {'type': 'string', 'value': ['1:f8:75:a4:aa:c9:e0']},
        #     'NAS-Identifier': {'type': 'string', 'value': ['OfficeTest']},
        #     'NAS-Port-Type': {'type': 'integer', 'value': [15]},
        #     'Event-Timestamp': {'type': 'date', 'value': ['Dec  2 2020 16:24:44 MSK']},
        #     'Agent-Remote-Id': {'type': 'octets', 'value': ['0x0006286ed47b1ca4']},
        #     'Agent-Circuit-Id': {'type': 'octets', 'value': ['0x000400040017']}
        # }

    @action(methods=['post'], detail=False)
    def acct(self, request):
        # return Response(status=status.HTTP_201_CREATED)
        # print('Acct:', request.data)
        # r_dhcp_op82 = {
        #     'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'],
        #     'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'],
        #     'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'],
        #     'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'],
        #     'Event-Timestamp': ['Dec  2 2020 16:29:45 MSK'], 'Acct-Status-Type': ['Interim-Update'],
        #     'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'],
        #     'Acct-Session-Time': ['0'],
        #     'Acct-Input-Octets': ['0'],
        #     'Acct-Input-Gigawords': ['0'],
        #     'Acct-Input-Packets': ['0'],
        #     'Acct-Output-Octets': ['71411'],
        #     'Acct-Output-Gigawords': ['0'],
        #     'Acct-Output-Packets': ['463'],
        #     'NAS-Identifier': ['OfficeTest'],
        #     'Acct-Delay-Time': ['1'],
        #     'NAS-IP-Address': ['10.12.2.10'],
        #     'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:29:46 MSK'], 'Tmp-String-9': ['ai:'],
        #     'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']
        # }
        # r2 = {
        #     'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'],
        #     'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'],
        #     'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'],
        #     'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'],
        #     'Event-Timestamp': ['Dec  2 2020 16:34:45 MSK'], 'Acct-Status-Type': ['Interim-Update'],
        #     'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'],
        #     'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'],
        #     'Acct-Output-Octets': ['84496'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['660'],
        #     'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['1'], 'NAS-IP-Address': ['10.12.2.10'],
        #     'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:34:46 MSK'], 'Tmp-String-9': ['ai:'],
        #     'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']
        # }

        # r4 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:39:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['93095'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['790'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['0'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:39:45 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # r5 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:39:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['93095'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['790'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['0'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:39:46 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # r6 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:39:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['93095'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['790'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['1'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:39:45 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # r7 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:44:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['114268'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['894'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['1'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:44:45 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # return Response(status=status.HTTP_204_NO_CONTENT)

        # FIXME: Pass name to 'vendor_name' from request
        vendor_manager = VendorManager(vendor_name='juniper')

        dat = request.data

        is_stop_radius_session = False
        act_type = _get_acct_rad_val(dat, 'Acct-Status-Type')
        # if act_type not in ['Start', 'Stop', 'Interim-Update', 'Accounting-On']:
        #     return _bad_ret('Bad Acct-Status-Type')
        if act_type == 'Stop':
            is_stop_radius_session = True

        # customer_mac = vendor_manager.get_customer_mac(request.data)
        # if customer_mac is None:
        #     return _bad_ret('Customer mac is required')

        ip = _get_acct_rad_val(dat, 'Framed-IP-Address')
        if ip is None:
            return _bad_ret('Framed-IP-Address required')

        agent_remote_id, agent_circuit_id = vendor_manager.get_opt82(
            data=request.data
        )

        if not all([agent_remote_id, agent_circuit_id]):
            return _bad_ret('Bad opt82')

        dev_mac, dev_port = vendor_manager.build_dev_mac_by_opt82(
            agent_remote_id=agent_remote_id,
            agent_circuit_id=agent_circuit_id
        )

        radius_username = _get_acct_rad_val(dat, 'User-Name')

        # create or update radius session
        UserSession.objects.create_or_update_session(
            session_id=_get_acct_rad_val(dat, 'Acct-Unique-Session-Id'),
            v_ip_addr=ip,
            v_dev_mac=dev_mac,
            v_dev_port=dev_port,
            v_sess_time=timedelta(seconds=safe_int(_get_acct_rad_val(dat, 'Acct-Session-Time', 0))),
            v_uname=radius_username,
            v_inp_oct=_gigaword_imp(
                num=_get_acct_rad_val(dat, 'Acct-Input-Octets', 0),
                gwords=_get_acct_rad_val(dat, 'Acct-Input-Gigawords', 0)
            ),
            v_out_oct=_gigaword_imp(
                num=_get_acct_rad_val(dat, 'Acct-Output-Octets', 0),
                gwords=_get_acct_rad_val(dat, 'Acct-Output-Gigawords', 0)
            ),
            v_in_pkt=_get_acct_rad_val(dat, 'Acct-Input-Packets', 0),
            v_out_pkt=_get_acct_rad_val(dat, 'Acct-Output-Packets', 0),
            v_is_stop=is_stop_radius_session
        )

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
