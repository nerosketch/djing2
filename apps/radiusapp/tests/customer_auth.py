"""Tests for fetching ip lease for customer."""
from django.test import override_settings
from rest_framework import status

from customers.tests.customer import CustomAPITestCase
from devices.tests import DeviceTestCase
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from services.models import Service


@override_settings(API_AUTH_SUBNET="127.0.0.0/8")
class CustomerAuthTestCase(CustomAPITestCase):
    """Main test case class."""

    def setUp(self):
        """Set up data for this tests."""
        super().setUp()
        # default_vlan = VlanIf.objects.filter(vid=1).first()

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

        self.client.logout()

    def _send_request(self, vlan_id: int, cid: str, arid: str, mac="18c0.4d51.dee2"):
        """Help method 4 send request to endpoint."""
        return self.post(
            "/api/radius/customer/auth/juniper/",
            {
                "User-Name": {"value": [f"18c0.4d51.dee2-ae0:{vlan_id}-{cid}-{arid}"]},
                "NAS-Port-Id": {"value": [vlan_id]},
                "ADSL-Agent-Circuit-Id": {"value": [f"0x{cid}"]},
                "ADSL-Agent-Remote-Id": {"value": [f"0x{arid}"]},
                "ERX-Dhcp-Mac-Addr": {"value": [mac]},
                "Acct-Unique-Session-Id": {"value": ["2ea5a1843334573bd11dc15417426f36"]},
            },
        )

    def test_guest_radius_session(self):
        """Just send simple request to not existed customer."""
        r = self._send_request(vlan_id=14, cid="0004008b000c", arid="0006286ED47B1CA4")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND, msg=r.content)

    def test_auth_radius_session(self):
        """Just send simple request to en existed customer."""
        r = self._send_request(vlan_id=12, cid="0004008B0002", arid="0006121314151617")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        self.assertEqual(r.data["User-Password"], self.service_inet_str, msg=r.content)

    def test_two_identical_fetch(self):
        """Repeat identical requests for same customer.
           Request must be deterministic."""
        r1 = self._send_request(vlan_id=12, cid="0004008B0002", arid="0006121314151617", mac="18c0.4d51.dee3")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        # self.assertEqual(r1.data["Framed-IP-Address"], "10.152.64.2")
        self.assertEqual(r1.data["User-Password"], self.service_inet_str)
        r2 = self._send_request(
            vlan_id=12, cid="0004008B0002", arid="0006121314151617", mac="18c0.4d51.dee4"
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        # self.assertEqual(r2.data["Framed-IP-Address"], "10.152.64.3")
        self.assertEqual(r2.data["User-Password"], self.service_inet_str)

    def test_guest_and_inet_subnet(self):
        """Проверка гостевой и инетной сессии.

        Проверяем что при включённой и выключенной услуге будет
        выдавать интернетную и гостевую сессию соответственно.
        """
        self.test_auth_radius_session()
        self.customer.stop_service(self.admin)
        r = self._send_request(vlan_id=12, cid="0004008B0002", arid="0006121314151617")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)