from django.test import override_settings
from rest_framework import status
from customers.tests.customer import CustomAPITestCase
from devices.tests import DeviceTestCase
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from services.models import Service
from networks.models import VlanIf, NetworkIpPool, NetworkIpPoolKind


@override_settings(API_AUTH_SUBNET="127.0.0.0/8")
class CustomerAcctStartTestCase(CustomAPITestCase):
    def setUp(self):
        """Set up data for this tests."""
        super().setUp()
        # default_vlan = VlanIf.objects.filter(vid=1).first()
        vlan12 = VlanIf.objects.create(title="Vlan for customer tests", vid=12)
        pool = NetworkIpPool.objects.create(
            network="10.152.64.0/24",
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            description="Test inet pool",
            ip_start="10.152.64.2",
            ip_end="10.152.64.254",
            vlan_if=vlan12,
            gateway="10.152.64.1",
            is_dynamic=True,
        )
        pool.groups.add(self.group)
        self.pool = pool

        # Create service for customer
        self.service = Service.objects.create(
            title="test", descr="test", speed_in=11.0, speed_out=11.0,
            cost=10.0, calc_type=SERVICE_CHOICE_DEFAULT
        )
        self.service_inet_str = "SERVICE-INET(11000000,2062500,11000000,2062500)"

        # Initialize devices instances
        DeviceTestCase.setUp(self)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.balance = 15
        self.customer.save()

        self.customer.pick_service(self.service, self.customer)

        # self.client.logout()

    def _send_request(self, vlan_id: int, cid: str, arid: str, ip="10.152.164.2", mac="18c0.4d51.dee2"):
        """Help method 4 send request to endpoint."""
        return self.post(
            "/api/radius/customer/acct/juniper/", {
                "User-Name": {"value": [f"18c0.4d51.dee2-ae0:{vlan_id}-{cid}-{arid}"]},
                "Acct-Status-Type": {"value": ["Start"]},
                "Framed-IP-Address": {"value": [ip]},
                "NAS-Port-Id": {"value": [vlan_id]},
                "ADSL-Agent-Circuit-Id": {"value": [f"0x{cid}"]},
                "ADSL-Agent-Remote-Id": {"value": [f"0x{arid}"]},
                "ERX-Dhcp-Mac-Addr": {"value": [mac]},
                "Acct-Unique-Session-Id": {"value": ["2ea5a1843334573bd11dc15417426f36"]},
            },
        )

    def _get_ip_leases(self) -> list:
        r = self.get(
            f"/api/networks/lease/?customer={self.customer.pk}",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertGreater(len(r.data), 0)
        return r.data

    def _get_rad_session_by_lease(self, lease_id: int):
        r = self.get(
            f"/api/radius/session/get_by_lease/{lease_id}/",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        return r.data

    def _create_acct_session(self):
        r = self._send_request(
            vlan_id=12,
            cid="0004008B0002",
            arid="0006121314151617",
            ip="10.152.64.6",
            mac="1c:c0:4d:95:d0:30"
        )
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, msg=r.content)

    def test_normal_new_session(self):
        self._create_acct_session()

        leases = self._get_ip_leases()
        self.assertEqual(len(leases), 1, msg=leases)
        lease = leases[0]
        self.assertEqual(lease['ip_address'], '10.152.64.6')
        self.assertEqual(lease['mac_address'], '1c:c0:4d:95:d0:30')
        self.assertEqual(lease['pool'], self.pool.pk)

        rad_ses = self._get_rad_session_by_lease(lease['id'])
        self.assertEqual(rad_ses['radius_username'], "18c0.4d51.dee2-ae0:12-0004008B0002-0006121314151617")
        self.assertEqual(rad_ses['session_id'], "2ea5a184-3334-573b-d11d-c15417426f36")
