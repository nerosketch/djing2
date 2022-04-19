"""Tests for fetching ip lease for customer."""
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from devices.device_config.switch.dlink.dgs_1100_10me import DEVICE_UNIQUE_CODE as Dlink_dgs1100_10me_code
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from profiles.models import UserProfile
from ._create_full_customer import create_full_customer


def radius_api_request_auth(vlan_id: int, cid: str, arid: str, mac: str):
    return {
        "User-Name": {"value": [f"18c0.4d51.dee2-ae0:{vlan_id}-{cid}-{arid}"]},
        "NAS-Port-Id": {"value": [vlan_id]},
        "ADSL-Agent-Circuit-Id": {"value": [f"0x{cid}"]},
        "ADSL-Agent-Remote-Id": {"value": [f"0x{arid}"]},
        "ERX-Dhcp-Mac-Addr": {"value": [mac]},
        "Acct-Unique-Session-Id": {"value": ["2ea5a1843334573bd11dc15417426f36"]},
    }


class ReqMixin:
    def get(self, *args, **kwargs):
        return self.client.get(SERVER_NAME="example.com", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(SERVER_NAME="example.com", *args, **kwargs)


@override_settings(API_AUTH_SUBNET="127.0.0.0/8")
class CustomerAuthTestCase(APITestCase, ReqMixin):
    """Main test case class."""

    def setUp(self):
        """Set up data for this tests."""
        #  super().setUp()
        # default_vlan = VlanIf.objects.filter(vid=1).first()
        self.admin = UserProfile.objects.create_superuser(
            username="admin", password="admin", telephone="+797812345678"
        )
        self.client.login(username="admin", password="admin")
        self.full_customer = create_full_customer(
            uname='custo1',
            tel='+797811234567',
            initial_balance=11,
            dev_ip="192.168.2.3",
            dev_mac="12:13:14:15:16:17",
            dev_type=Dlink_dgs1100_10me_code,
            service_title='test',
            service_descr='test',
            service_speed_in=11.0,
            service_speed_out=11.0,
            service_cost=10.0,
            service_calc_type=SERVICE_CHOICE_DEFAULT
        )
        self.service_inet_str = "SERVICE-INET(11000000,2062500,11000000,2062500)"
        #  self.client.logout()

    def _send_request(self, vlan_id: int, cid: str, arid: str, mac="18c0.4d51.dee2"):
        """Help method 4 send request to endpoint."""
        return self.post(
            "/api/radius/customer/auth/juniper/",
            radius_api_request_auth(vlan_id, cid, arid, mac)
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
        r1 = self._send_request(
            vlan_id=12, cid="0004008B0002",
            arid="0006121314151617", mac="18c0.4d51.dee3"
        )
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
        customer = self.full_customer.customer
        self.test_auth_radius_session()
        customer.stop_service(self.admin)
        r = self._send_request(vlan_id=12, cid="0004008B0002", arid="0006121314151617")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        self.assertDictEqual(r.data, {"User-Password": "SERVICE-GUEST"})

