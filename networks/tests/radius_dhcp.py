from django.test import TestCase

from networks.tests import FetchSubscriberDynamicLeaseTestCase


class RadiusDHCPRequestTestCase(TestCase):
    def setUp(self):
        FetchSubscriberDynamicLeaseTestCase.setUp(self)

    def test_get_new_ip(self):
        r = self.client.post('/api/networks/radius/dhcp_request/', data={
            'opt82': {
                'remote_id': b'\x12\x13\x14\x15\x16\x17',  # 12:13:14:15:16:17
                'circuit_id': b'\x12\x13\x14\x15\x16\x02'  # port #2
            },
            'client_mac': '1:2:3:4:5:6'
        })
        self.assertEqual(r.status_code, 200)
        self.assertJSONEqual(r.data, {
            "control:Auth-Type": 'Accept',
            "Framed-IP-Address": '10.11.12.2',
            "DHCP-Your-IP-Address": '10.11.12.2',
            "DHCP-Subnet-Mask": '255.255.255.0',
            "DHCP-Router-Address": '10.11.12.1',
            "DHCP-IP-Address-Lease-Time": 300,
        })
