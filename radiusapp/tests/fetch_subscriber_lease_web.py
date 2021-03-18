"""Tests for fetching ip lease for customer."""
from rest_framework import status
from customers.tests.customer import CustomAPITestCase
from devices.tests import DeviceTestCase
from networks.models import NetworkIpPool, NetworkIpPoolKind, VlanIf
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from services.models import Service


class FetchSubscriberLeaseWebApiTestCase(CustomAPITestCase):
    """Main test case class."""

    def setUp(self):
        """Set up data for this tests."""
        super().setUp()
        default_vlan = VlanIf.objects.filter(vid=1).first()
        guest_pool = NetworkIpPool.objects.create(
            network='10.255.0.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_GUEST,
            description='Test guest pool',
            ip_start='10.255.0.2',
            ip_end='10.255.0.254',
            vlan_if=default_vlan,
            gateway='10.255.0.1',
            is_dynamic=True
        )
        self.guest_pool = guest_pool
        vlan12 = VlanIf.objects.create(
            title='Vlan for customer tests',
            vid=12
        )
        pool = NetworkIpPool.objects.create(
            network='10.152.64.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            description='Test guest pool',
            ip_start='10.152.64.2',
            ip_end='10.152.64.254',
            vlan_if=vlan12,
            gateway='10.152.64.1',
            is_dynamic=True
        )
        pool.groups.add(self.group)
        self.pool = pool

        # Create service for customer
        self.service = Service.objects.create(
            title='test',
            descr='test',
            speed_in=11.0,
            speed_out=11.0,
            cost=10.0,
            calc_type=SERVICE_CHOICE_DEFAULT
        )

        # Initialize devices instances
        DeviceTestCase.setUp(self)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.balance = 15
        self.customer.save()

        self.customer.pick_service(self.service, self.customer)

    def _send_request(self, vlan_id: int, cid: str, arid: str,
                      existing_ip='10.152.164.2', mac='18c0.4d51.dee2'):
        """Help method 4 send request to endpoint."""
        return self.post('/api/radius/customer/auth/juniper/', {
            "User-Name": {
                "value": [f"18c0.4d51.dee2-ae0:{vlan_id}-{cid}-{arid}"]},
            "Framed-IP-Address": {"value": [existing_ip]},
            "NAS-Port": {"value": [vlan_id]},
            "ADSL-Agent-Circuit-Id": {"value": [f"0x{cid}"]},
            "ADSL-Agent-Remote-Id": {"value": [f"0x{arid}"]},
            "ERX-Dhcp-Mac-Addr": {"value": [mac]},
            "Acct-Unique-Session-Id": {
                "value": ["2ea5a1843334573bd11dc15417426f36"]}
        })

    def test_guest_radius_session(self):
        """Just send simple request to not existed customer."""
        r = self._send_request(vlan_id=14, cid='0004008b000c',
                               arid='0006286ED47B1CA4')
        self.assertDictEqual(r.data, {
            "Framed-IP-Address": "10.255.0.2",
            "User-Password": "SERVICE-GUEST"
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_auth_radius_session(self):
        """Just send simple request to existed customer."""
        r = self._send_request(vlan_id=12, cid='0004008B0002',
                               arid='0006121314151617')
        self.assertDictEqual(r.data, {
            "Framed-IP-Address": "10.152.64.2",
            "User-Password": "SERVICE-INET(11000000,2062500,11000000,2062500)"
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_two_identical_fetch(self):
        """Repeat identical requests for same customer."""
        r1 = self._send_request(
            vlan_id=12, cid='0004008B0002',
            arid='0006121314151617',
            mac='18c0.4d51.dee3'
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertDictEqual(r1.data, {
            "Framed-IP-Address": "10.152.64.2",
            "User-Password": "SERVICE-INET(11000000,2062500,11000000,2062500)"
        })
        r2 = self._send_request(
            vlan_id=12, cid='0004008B0002',
            arid='0006121314151617',
            mac='18c0.4d51.dee4',
            existing_ip='10.152.16473'
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertDictEqual(r2.data, {
            "Framed-IP-Address": "10.152.64.3",
            "User-Password": "SERVICE-INET(11000000,2062500,11000000,2062500)"
        })

    def test_guest_and_inet_subnet(self):
        """Проверка гостевой и инетной аренды ip.

        Проверяем что при включённой и выключенной услуге будет
        выдавать интернетный и гостевой ip соответственно, при условии что
        интернетный ip на мак уже выдан.
        """
        self.test_auth_radius_session()
        self.customer.stop_service(self.admin)
        r = self._send_request(vlan_id=12, cid='0004008B0002',
                               arid='0006121314151617')
        self.assertDictEqual(r.data, {
            "Framed-IP-Address": "10.255.0.2",
            "User-Password": "SERVICE-GUEST"
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    # def test_subnet_vid(self):
    #     """Проверяем чтоб ip выдавались в соответствии в переданным
    #        vid. Или с первого доступного пула для группы, если vid
    #        не передан.
    #     """
    #     res = CustomerRadiusSession.objects.fetch_subscriber_lease(
    #         customer_mac='aa:bb:cc:dd:ee:f1',
    #         customer_id=self.customer.pk,
    #         customer_group=self.customer.group_id,
    #         is_dynamic=True,
    #         vid=12,
    #         pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET
    #     )
