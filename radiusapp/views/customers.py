from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from customers.models import CustomerService
from customers.serializers import RadiusCustomerServiceRequestSerializer
from djing2.viewsets import DjingAuthorizedViewSet
from radiusapp.models import parse_opt82
from services.models import Service


def _get_rad_val(data, v: str):
    k = data.get(v)
    if k:
        k = k.get('value')
        if k:
            return k[0]


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
            return Response('Customer service not found', status=status.HTTP_404_NOT_FOUND)

        sess_time = customer_service.calc_session_time()
        return Response({
            'ip': customer_ip,
            'session_time': int(sess_time.total_seconds()),
            'speed_in': customer_service.service.speed_in,
            'speed_out': customer_service.service.speed_out
        })

    @action(methods=['post'], detail=False)
    def auth(self, request):
        # print('Auth:', request.data)
        aget_remote_id = _get_rad_val(request.data, 'Agent-Remote-Id')
        aget_circ_id = _get_rad_val(request.data, 'Agent-Circuit-Id')
        # event_time = _get_rad_val(request.data, 'Event-Timestamp')
        # ip = _get_rad_val(request.data, 'Framed-IP-Address')  # possible none

        if not all([aget_remote_id, aget_circ_id]):
            return Response(status=status.HTTP_403_FORBIDDEN)

        dig = int(aget_remote_id, base=16)
        aget_remote_id = dig.to_bytes((dig.bit_length() + 7) // 8, 'big')
        dig = int(aget_circ_id, base=16)
        aget_circ_id = dig.to_bytes((dig.bit_length() + 7) // 8, 'big')

        dev_mac, dev_port = parse_opt82(aget_remote_id, aget_circ_id)

        if dev_mac is None:
            return Response('Failed to parse option82', status=status.HTTP_403_FORBIDDEN)

        service = Service.find_customer_service_by_device_credentials(
            dev_mac=dev_mac,
            dev_port=dev_port
        )
        if service is None:
            return Response('Service not found', status=status.HTTP_403_FORBIDDEN)
        sin, sout = int(service.speed_in * 0x400), int(service.speed_out * 0x400)
        speed = f"{sin}k/{sout}k"
        return Response({
            'Mikrotik-Rate-Limit': speed,
            # 'Session-Timeout': 15
        })
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
        #
        # r4 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:39:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['93095'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['790'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['0'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:39:45 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # r5 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:39:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['93095'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['790'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['0'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:39:46 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # r6 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:39:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['93095'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['790'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['1'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:39:45 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # r7 = {'User-Name': ['F8:75:A4:AA:C9:E0'], 'NAS-Port-Type': ['Ethernet'], 'NAS-Port': ['2212495516'], 'Service-Type': ['Framed-User'], 'Calling-Station-Id': ['1:f8:75:a4:aa:c9:e0'], 'Framed-IP-Address': ['192.168.3.50'], 'Called-Station-Id': ['mypool'], 'Agent-Remote-Id': ['0x0006286ed47b1ca4'], 'Agent-Circuit-Id': ['0x000400040017'], 'Event-Timestamp': ['Dec  2 2020 16:44:45 MSK'], 'Acct-Status-Type': ['Interim-Update'], 'Acct-Session-Id': ['9c00e083'], 'Acct-Authentic': ['RADIUS'], 'Acct-Session-Time': ['0'], 'Acct-Input-Octets': ['0'], 'Acct-Input-Gigawords': ['0'], 'Acct-Input-Packets': ['0'], 'Acct-Output-Octets': ['114268'], 'Acct-Output-Gigawords': ['0'], 'Acct-Output-Packets': ['894'], 'NAS-Identifier': ['OfficeTest'], 'Acct-Delay-Time': ['1'], 'NAS-IP-Address': ['10.12.2.10'], 'FreeRADIUS-Acct-Session-Start-Time': ['Dec  2 2020 16:44:45 MSK'], 'Tmp-String-9': ['ai:'], 'Acct-Unique-Session-Id': ['b51db081c208510befe067ae1507d79f']}
        # return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_403_FORBIDDEN)
        # return Response({
        #     'Acct-Interim-Interval': 300,
        #     # 'Mikrotik-Address-List': 'DjingUsersAllowed',
        #     'Mikrotik-Rate-Limit': '50M/43M'
        # })
