from rest_framework import status
from customers.tests.customer import CustomAPITestCase
from networks.models import NetworkIpPool, NetworkIpPoolKind, VlanIf


class FetchSubscriberLeaseWebApiTestCase(CustomAPITestCase):
    def setUp(self):
        super().setUp()
        vlan1 = VlanIf.objects.create(
            title='Vlan for customer tests',
            vid=12
        )
        pool = NetworkIpPool.objects.create(
            network='10.255.0.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_GUEST,
            description='Test guest pool',
            ip_start='10.255.0.2',
            ip_end='10.255.0.254',
            vlan_if=vlan1,
            gateway='10.255.0.1',
            is_dynamic=True
        )
        self.pool = pool

    def test_guest_radius_session(self):
        r = self.post('/api/radius/customer/auth/', {
            "User-Name": {"value": ["18c0.4d51.dee2-ae0:139-0004008B000C-0006286ED47B1CA4"]},
            "Framed-IP-Address": {"value": ["10.152.164.2"]},
            "NAS-Port": {"value": [12]},
            "ADSL-Agent-Circuit-Id": {"value": ["0x0004008b000c"]},
            "ADSL-Agent-Remote-Id": {"value": ["0x0006286ed47b1ca4"]},
            "ERX-Dhcp-Mac-Addr": {"value": ["18c0.4d51.dee2"]},
            "Acct-Unique-Session-Id": {"value": ["2ea5a1843334573bd11dc15417426f36"]}
        })
        self.assertDictEqual(r.data, {
            "Framed-IP-Address": "10.255.0.2",
            "ERX-Service-Activate:1": "SERVICE-INET(10000000,1875000,10000000,1875000)"
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
