import base64

from rest_framework.test import APITestCase

from networks.models import NetworkIpPool
from networks.tests import FetchSubscriberDynamicLeaseTestCase


class RadiusDHCPRequestTestCase(APITestCase):
    def setUp(self):
        FetchSubscriberDynamicLeaseTestCase.setUp(self)

    def _make_dhcp_request(self, remote_id: bytes, circuit_id: bytes, client_mac: str, expected_ip: str, status_code=200, gw_ip='10.11.12.1'):
        r = self.client.post('/api/networks/radius/dhcp_request/', data={
            'opt82': {
                'remote_id': base64.b64encode(remote_id),
                'circuit_id': base64.b64encode(circuit_id)
            },
            'client_mac': client_mac
        })
        self.assertEqual(r.status_code, status_code)
        self.assertDictEqual(r.data, {
            "control:Auth-Type": 'Accept',
            "Framed-IP-Address": expected_ip,
            "DHCP-Your-IP-Address": expected_ip,
            "DHCP-Subnet-Mask": '255.255.255.0',
            "DHCP-Router-Address": gw_ip,
            "DHCP-IP-Address-Lease-Time": 86400,
        })

    def test_get_new_ip(self):
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',      # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',     # port #2
            client_mac='1:2:3:4:5:6',
            expected_ip='10.11.12.2'
        )

    def test_multiple_fetch(self):
        for n in range(4):
            self._make_dhcp_request(
                remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
                circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
                client_mac='1:2:3:4:5:7',
                expected_ip='10.11.12.2'
            )

    def test_different_mac(self):
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
            client_mac='1:2:3:4:5:6',
            expected_ip='10.11.12.2'
        )
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
            client_mac='1:2:3:4:5:7',
            expected_ip='10.11.12.3'
        )

    def test_multiple_customers(self):
        # self.customer, switch device
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
            client_mac='1:2:3:4:5:6',
            expected_ip='10.11.12.2'
        )
        # self.customer2, onu device
        self._make_dhcp_request(
            remote_id=b'\x11\x13\x14\x15\x16\x18',  # 12:13:14:15:16:18
            circuit_id=b'\x00',
            client_mac='1:2:3:4:5:8',
            expected_ip='10.11.12.3'
        )

    def test_ident_mac(self):
        for n in range(4):
            # self.customer, switch device with user mac 1:2:3:4:5:6
            self._make_dhcp_request(
                remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
                circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
                client_mac='1:2:3:4:5:6',
                expected_ip='10.11.12.2'
            )
            # self.customer2, onu device with the same user mac 1:2:3:4:5:6
            self._make_dhcp_request(
                remote_id=b'\x11\x13\x14\x15\x16\x18',  # 12:13:14:15:16:18
                circuit_id=b'\x00',
                client_mac='1:2:3:4:5:6',
                expected_ip='10.11.12.3'
            )

    def test_change_subnet(self):
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
            client_mac='1:2:3:4:5:6',
            expected_ip='10.11.12.2'
        )
        ippool2 = NetworkIpPool.objects.create(
            network='10.10.11.0/24',
            kind=NetworkIpPool.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.10.11.2',
            ip_end='10.10.11.254',
            gateway='10.10.11.1'
        )
        self.ippool.groups.remove(self.group)
        ippool2.groups.add(self.group)
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
            client_mac='1:2:3:4:5:6',
            expected_ip='10.10.11.2',
            gw_ip='10.10.11.1'
        )
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
            client_mac='1:2:3:4:5:7',
            expected_ip='10.10.11.3',
            gw_ip='10.10.11.1'
        )
        self._make_dhcp_request(
            remote_id=b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
            circuit_id=b'\x12\x13\x14\x15\x16\x02',  # port #2
            client_mac='1:2:3:4:5:6',
            expected_ip='10.10.11.2',
            gw_ip='10.10.11.1'
        )
