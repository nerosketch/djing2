"""Tests for fetching ip lease for customer."""
from typing import Optional
from dataclasses import dataclass
from django.test import override_settings
from django.db.models import signals
from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.sites.models import Site
from customers.models import Customer
from devices.models import Device, Port
from devices.device_config.pon.gpon.onu_zte_f601 import DEVICE_UNIQUE_CODE as OnuZTE_F601_code
from devices.device_config.switch.dlink.dgs_1100_10me import DEVICE_UNIQUE_CODE as Dlink_dgs1100_10me_code
from groupapp.models import Group
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from services.models import Service
from profiles.models import UserProfile


@dataclass
class CreateFullCustomerReturnType:
    group: Group
    customer: Customer
    device: Device
    service: Service
    site: Optional[Site]


def create_full_customer(uname: str,
                         tel: str,
                         dev_type: int,
                         dev_mac: Optional[str] = None,
                         dev_ip: Optional[str] = None,
                         group_title: Optional[str] = None,
                         service_title: Optional[str] = None,
                         service_descr: Optional[str] = None,
                         service_speed_in=11.0,
                         service_speed_out=11.0,
                         service_cost=10,
                         service_calc_type=SERVICE_CHOICE_DEFAULT,
                         initial_balance=0,
                         dev_comment: Optional[str] = None) -> CreateFullCustomerReturnType:
    if group_title is None:
        group_title = 'test_group'

    group, group_is_created = Group.objects.get_or_create(title=group_title, code="tst")

    if dev_mac is None:
        dev_mac = "11:13:14:15:17:17"

    if dev_comment is None:
        dev_comment = 'device for tests'

    # Other device for other customer
    device = Device.objects.create(
        mac_addr=dev_mac, comment=dev_comment,
        dev_type=dev_type, ip_address=dev_ip,
    )
    ports = tuple(Port(device=device, num=n, descr="test %d" % n) for n in range(1, 3))
    ports = Port.objects.bulk_create(ports)

    customer = Customer.objects.create_user(
        telephone=tel, username=uname, password="passw",
        is_dynamic_ip=True, group=group,
        balance=initial_balance, device=device,
        dev_port=ports[1]
    )

    example_site = Site.objects.first()
    if example_site:
        customer.sites.add(example_site)
    customer.refresh_from_db()

    if service_title is None:
        service_title = 'test service'
    if service_descr is None:
        service_descr = 'test service description'
    # Create service for customer
    service, service_is_created = Service.objects.get_or_create(
        title=service_title, descr=service_descr,
        speed_in=service_speed_in,
        speed_out=service_speed_out,
        cost=service_cost,
        calc_type=service_calc_type
    )
    customer.pick_service(service, customer)
    return CreateFullCustomerReturnType(
        group=group,
        customer=customer,
        site=example_site,
        device=device,
        service=service
    )



def radius_api_request_auth(vlan_id: int, cid: str, arid: str, mac: str):
    return {
        "User-Name": {"value": [f"18c0.4d51.dee2-ae0:{vlan_id}-{cid}-{arid}"]},
        "NAS-Port-Id": {"value": [vlan_id]},
        "ADSL-Agent-Circuit-Id": {"value": [f"0x{cid}"]},
        "ADSL-Agent-Remote-Id": {"value": [f"0x{arid}"]},
        "ERX-Dhcp-Mac-Addr": {"value": [mac]},
        "Acct-Unique-Session-Id": {"value": ["2ea5a1843334573bd11dc15417426f36"]},
    }

def radius_api_request_acct(vlan_id: int, cid: str, arid: str, mac: str, ip: str):
    return {
        "User-Name": {"value": [f"18c0.4d51.dee2-ae0:{vlan_id}-{cid}-{arid}"]},
        "NAS-Port-Id": {"value": [vlan_id]},
        "ADSL-Agent-Circuit-Id": {"value": [f"0x{cid}"]},
        "ADSL-Agent-Remote-Id": {"value": [f"0x{arid}"]},
        "ERX-Dhcp-Mac-Addr": {"value": [mac]},
        "Acct-Unique-Session-Id": {"value": ["2ea5a1843334573bd11dc15417426f36"]},
        "Framed-IP-Address": {"value": [ip]}
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


@override_settings(API_AUTH_SUBNET="127.0.0.0/8")
class TestClonedMac(APITestCase, ReqMixin):
    """Проверяем что будет если 2 абонента с одинаковым маком попытаются получить ip.
       Такое бывает когда клонировали мак на роутере.
       Сессия должна выдаться на учётку, которая подходит по opt82,
       если opt82 имеется. Если нет, то тогда уже доверяем маку, т.к. не остаётся вариантов."""

    def _send_request_auth(self, vlan_id: int, cid: str, arid: str, mac: str):
        """Help method 4 send request to endpoint."""
        return self.post(
            "/api/radius/customer/auth/juniper/",
            radius_api_request_auth(
                vlan_id=vlan_id,
                cid=cid,
                arid=arid,
                mac=mac
            )
        )

    def _send_request_acct(self, vlan_id: int, cid: str, arid: str, mac: str, ip: str):
        """Help method 4 send request to endpoint."""
        return self.post(
            "/api/radius/customer/acct/juniper/",
            radius_api_request_acct(
                vlan_id=vlan_id,
                cid=cid,
                arid=arid,
                mac=mac,
                ip=ip
            )
        )

    def setUp(self):
        """Set up data for this tests."""
        super().setUp()
        # default_vlan = VlanIf.objects.filter(vid=1).first()
        signals.post_save.disconnect()
        signals.post_delete.disconnect()
        signals.pre_save.disconnect()
        signals.pre_delete.disconnect()

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
        self.full_customer2 = create_full_customer(
            uname='custo2',
            tel='+79782345679',
            initial_balance=11,
            dev_ip="192.168.2.4",
            dev_mac="11:13:14:15:17:17",
            dev_type=OnuZTE_F601_code,
            dev_comment='test3',
            service_title='tess',
            service_descr='tess',
            service_speed_in=12.0,
            service_speed_out=12.0,
            service_cost=3.0,
            service_calc_type=SERVICE_CHOICE_DEFAULT
        )
        #  self.service_inet_str = "SERVICE-INET(11000000,2062500,11000000,2062500)"
        #  self.client.logout()

    def _check_customer_network_leases(self, customer_id: int):
        r = self.get(
            '/api/networks/lease/?customer=%d' % customer_id
        )
        d = r.data
        self.assertEqual(r.status_code, 200, msg=r.content)
        for i in d:
            self.assertEqual(i['customer'], customer_id, msg=i)
        return d

    def test_two_customers_with_cloned_mac(self):
        r = self._send_request_acct(
            vlan_id=12,
            cid='0004008B0002',
            arid='0006121314151617',
            mac='18c0.4d51.dee4',
            ip='192.168.2.2'
        )
        #  print('R1', r.content)

        #customer = self.full_customer.customer
        #net_dat = self._check_customer_network_leases(
        #    customer_id=customer.pk
        #)
        #print('R1 NetData:', net_dat)
        ## Какие-то данные дожны быть
        #self.assertGreaterEqual(len(net_dat), 1, msg='Customer profile network leases is empty')

        r2 = self._send_request_auth(
            vlan_id=12,
            cid='0004008B8002',
            arid='0006111314151717',
            mac='18c0.4d51.dee4',
        )
        #  print('R2', r2.content)
        self.assertEqual(r.status_code, 200, msg=r.content)
        self.assertEqual(r2.status_code, 200, msg=r2.content)

    def test_two_leases_on_customer_profile(self):
        """Тестируем когда на учётке больше одного ip, и пробуем его получить.
           Должно выдавать по opt82, если есть в запросе, если нет то по маку, если он есть в ip лизе.
        """
        pass
