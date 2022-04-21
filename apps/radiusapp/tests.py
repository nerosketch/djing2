from typing import Optional
from dataclasses import dataclass
from django.contrib.sites.models import Site
from django.db.models import signals
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from customers.models import Customer
from devices.models import Device, Port
from devices.device_config.switch.dlink.dgs_1100_10me import DEVICE_UNIQUE_CODE as Dlink_dgs1100_10me_code
from groupapp.models import Group
from services.models import Service
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from profiles.models import UserProfile
from radiusapp.vendors import VendorManager, parse_opt82
from radiusapp.models import CustomerRadiusSession
from networks.models import (
    VlanIf, NetworkIpPool,
    NetworkIpPoolKind,
    CustomerIpLeaseModel
)


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

    group, _ = Group.objects.get_or_create(title=group_title, code="tst")

    if dev_mac is None:
        dev_mac = "11:13:14:15:17:17"

    if dev_comment is None:
        dev_comment = 'device for tests'

    # Other device for other customer
    device, _ = Device.objects.get_or_create(
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



class VendorsBuildDevMacByOpt82TestCase(SimpleTestCase):
    def _make_request(self, remote_id: str, circuit_id: str):
        dev_mac, dev_port = VendorManager.build_dev_mac_by_opt82(
            agent_remote_id=remote_id, agent_circuit_id=circuit_id
        )
        return dev_mac, dev_port

    def test_parse_opt82_ok(self):
        circuit_id = "0x000400980005"
        rem_id = "0x0006f8e903e755a6"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "f8:e9:03:e7:55:a6")
        self.assertEqual(port, 5)

    def test_parse_opt82_ok2(self):
        circuit_id = "0x00007400071d"
        rem_id = "0x00061c877912e61a"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 29)

    def test_parse_opt82_long_data(self):
        circuit_id = "0x007400ff1dff01"
        rem_id = "0x0006ff121c877912e61a"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 1)

    def test_parse_opt82_short_data(self):
        circuit_id = "0x007400ff"
        rem_id = "0x1c8779"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertIsNone(mac)
        self.assertEqual(port, 255)

    def test_parse_opt82_ok_zte(self):
        circuit_id = "0x5a5445474330323838453730"
        rem_id = "0x34353a34373a63303a32383a38653a3730"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c0:28:8e:70")
        self.assertEqual(port, 0)

    def test_parse_opt82_ok_zte2(self):
        circuit_id = "0x5a5445474334303235334233"
        rem_id = "0x34353a34373a63343a323a35333a6233"
        mac, port = self._make_request(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c4:2:53:b3")
        self.assertEqual(port, 0)


@override_settings(API_AUTH_SUBNET="127.0.0.0/8")
class CustomerAcctStartTestCase(APITestCase):
    def get(self, *args, **kwargs):
        return self.client.get(SERVER_NAME="example.com", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(SERVER_NAME="example.com", *args, **kwargs)

    def setUp(self):
        """Set up data for this tests."""
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
            tel='+797811234568',
            initial_balance=11,
            dev_ip="192.168.3.3",
            dev_mac="13:13:14:15:17:17",
            dev_type=Dlink_dgs1100_10me_code,
            service_title='test',
            service_descr='test',
            service_speed_in=11.0,
            service_speed_out=11.0,
            service_cost=10.0,
            service_calc_type=SERVICE_CHOICE_DEFAULT
        )

        vlan12 = VlanIf.objects.create(title="Vlan12 for customer tests", vid=12)
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
        vlan13 = VlanIf.objects.create(title="Vlan13 for customer tests", vid=13)
        poolv13 = NetworkIpPool.objects.create(
            network="10.152.65.0/24",
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            description="Test inet pool13",
            ip_start="10.152.65.2",
            ip_end="10.152.65.254",
            vlan_if=vlan13,
            gateway="10.152.65.1",
            is_dynamic=False,
        )
        group = self.full_customer.group
        pool.groups.add(group)
        poolv13.groups.add(group)
        self.pool = pool
        self.poolv13 = poolv13

        self.service_inet_str = "SERVICE-INET(11000000,2062500,11000000,2062500)"

        # self.client.logout()

    def _send_request_acct(self, cid: str, arid: str, vlan_id: int = 0, ip="10.152.164.2", mac="18c0.4d51.dee2"):
        """Help method 4 send request to acct endpoint.
           Важно: vlan_id (NAS-Port-Id) сейчас не влияет на логику radius accounting в билинге.
        """
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

    def _send_request_auth(self, cid: str, arid: str, mac: str, vlan_id: int = 0):
        return self.post(
            "/api/radius/customer/auth/juniper/",
            radius_api_request_auth(
                vlan_id=vlan_id,
                cid=cid,
                arid=arid,
                mac=mac
            )
        )

    def _get_ip_leases(self, customer_id: Optional[int] = None) -> list:
        if customer_id is None:
            customer_id = self.full_customer.customer.pk
        r = self.get(
            f"/api/networks/lease/?customer={customer_id}",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        self.assertGreater(len(r.data), 0)
        return r.data

    def _get_rad_session_by_lease(self, lease_id: int):
        r = self.get(
            f"/api/radius/session/get_by_lease/{lease_id}/",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        self.assertIsNotNone(r.data, msg=r.content)
        return r.data

    def _create_acct_session(self, vid=12, cid="0004008B0002", arid="0006121314151617",
                             ip="10.152.64.6", mac="1c:c0:4d:95:d0:30"):
        r = self._send_request_acct(
            vlan_id=vid,
            cid=cid,
            arid=arid,
            ip=ip,
            mac=mac,
        )
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, msg=r.content)
        self.assertIsNone(r.data)

    def _create_static_lease(self, ip):
        new_lease_r = self.post(
            "/api/networks/lease/", {
                "customer": self.full_customer.customer.pk,
                "ip_address": ip,
                # "mac_address": "",
                "pool": self.pool.pk
            }
        )
        self.assertEqual(new_lease_r.status_code, status.HTTP_201_CREATED, new_lease_r.content)
        return new_lease_r

    def test_normal_new_session(self):
        self._create_acct_session()

        leases = self._get_ip_leases()
        self.assertEqual(len(leases), 1, msg=leases)
        lease = leases[0]
        self.assertEqual(lease['ip_address'], '10.152.64.6')
        self.assertEqual(lease['mac_address'], '1c:c0:4d:95:d0:30')
        self.assertEqual(lease['customer'], self.full_customer.customer.pk)
        self.assertEqual(lease['pool'], self.pool.pk)

        rad_ses = self._get_rad_session_by_lease(lease['id'])
        self.assertEqual(rad_ses['customer'], self.full_customer.customer.pk)
        self.assertEqual(rad_ses['radius_username'], "18c0.4d51.dee2-ae0:12-0004008B0002-0006121314151617")
        self.assertEqual(rad_ses['session_id'], "2ea5a184-3334-573b-d11d-c15417426f36")

    def test_get_fixed_ip_without_mac(self):
        ip = '10.152.64.16'
        # Создаём статический lease с ip и без мака
        self._create_static_lease(ip=ip)

        # делаем запрос от радиуса
        self._create_acct_session(
            ip=ip
        )

        # Пробуем получить этот ip по оборудованию, которое назначено на учётку абонента
        leases = self._get_ip_leases()
        # На выходе должны получить эту lease
        self.assertEqual(len(leases), 1, msg=leases)
        lease = leases[0]
        self.assertEqual(lease['ip_address'], ip)
        self.assertIsNone(lease['mac_address'])
        self.assertEqual(lease['pool'], self.pool.pk)
        self.assertEqual(lease['customer'], self.full_customer.customer.pk)

        # Проверяем CustomerRadiusSession, должен был создаться для этой lease
        rad_ses = self._get_rad_session_by_lease(lease['id'])
        self.assertIsNotNone(rad_ses['radius_username'])
        self.assertIsNotNone(rad_ses['session_id'])
        self.assertEqual(rad_ses['ip_lease'], lease['id'])
        self.assertEqual(rad_ses['ip_lease_ip'], lease['ip_address'])
        self.assertEqual(rad_ses['customer'], self.full_customer.customer.pk)

    # Проверить что происходит когда запрашиваем ip у другого абонента, не у того, кому он выдан.

    def test_get_ip_with_not_existed_pool(self):
        # Если выделен ip из несуществующей подсети то в билинге нужно показать этот неправильный ip
        ip = '172.16.3.2'
        mac = '11:c3:6d:95:d9:33'
        self._create_acct_session(
            ip=ip,
            mac=mac
        )

        # Пробуем получить этот ip по оборудованию, которое назначено на учётку абонента
        leases = self._get_ip_leases()
        # На выходе должны получить эту lease без ip pool
        self.assertEqual(len(leases), 1, msg=leases)
        lease = leases[0]
        self.assertEqual(lease['ip_address'], ip)
        self.assertEqual(lease['mac_address'], mac)
        self.assertIsNone(lease['pool'])
        self.assertEqual(lease['customer'], self.full_customer.customer.pk)

    def test_two_leases_on_customer_profile(self):
        """Тестируем когда на учётке больше одного ip, и пробуем их получить.
        """
        # Создаём динамический ip в vlan 12,
        # ip 10.152.64.6
        # мак 1c:c0:4d:95:d0:30
        self.test_normal_new_session()

        # Создадим статичный ip на учётке в vlan 13, 10.152.65.16
        self.post(
            "/api/networks/lease/", {
                "customer": self.full_customer.customer.pk,
                "ip_address": '10.152.65.16',
                # "mac_address": "",
                "pool": self.poolv13.pk
            }
        )

        leases = self._get_ip_leases()
        self.assertEqual(len(leases), 2, msg='Must be two leases on account')

        # Пробуем получить статический ip vlan13
        r = self._send_request_auth(
            #  vlan_id=13,
            cid='0004008B0002',
            arid='0006121314151617',
            mac='1c:c0:4d:95:d0:38'
        )
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['Framed-IP-Address'], '10.152.65.16')

        # Пробуем получить динамичекий ip vlan12
        r = self._send_request_auth(
            #  vlan_id=12,
            cid='0004008B0002',
            arid='0006121314151617',
            mac='1c:c0:4d:95:d0:30'
        )
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['Framed-IP-Address'], '10.152.64.6')

    def test_creating_new_dynamic_session_with_different_client_mac(self):
        """Проверяем чтобы на учётку создавались новые сессии и ip когда
           приходят запросы с разными маками от оборудования клиента.
        """
        # Создаём первую сессию.
        self.test_normal_new_session()

        # Создаём вторую сессию
        self._create_acct_session(
            vid=13,
            cid='0004008B0002',
            arid='0006121314151617',
            ip='10.152.65.17',
            mac='1c:c0:4d:95:d0:31',
        )

        leases = self._get_ip_leases()
        self.assertEqual(len(leases), 2, msg=leases)

        leasev12, leasev13 = leases
        self.assertEqual(leasev12['ip_address'], '10.152.64.6')
        self.assertEqual(leasev12['mac_address'], '1c:c0:4d:95:d0:30')
        self.assertEqual(leasev12['customer'], self.full_customer.customer.pk)
        self.assertEqual(leasev12['pool'], self.pool.pk)
        # ---------
        self.assertEqual(leasev13['ip_address'], '10.152.65.17')
        self.assertEqual(leasev13['mac_address'], '1c:c0:4d:95:d0:31')
        self.assertEqual(leasev13['customer'], self.full_customer.customer.pk)
        self.assertEqual(leasev13['pool'], self.poolv13.pk)

    #def test_guest_session_while_unknown_opt82_credentials(self):
    #    """Если по opt82 мы нашли учётку, ..."""
    #    pass

    def test_profile_not_found_then_global_guest_session(self):
        """Если по opt82 не находим учётку, то создаём гостевую
           сессию без учётки.
        """
        r = self._send_request_acct(
            # Not existing credentials
            cid='0004008B0003',
            arid='0006121314151618',
            ip='10.152.65.17',
            mac='1c:c0:4d:95:d0:31',
        )
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, msg=r.content)
        self.assertIsNone(r.data)

        # Получаем все гостевые аренды
        r = self.get(
            "/api/radius/session/guest_list/"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        d = r.data
        self.assertGreaterEqual(len(d), 1)
        #  print('Data:', d)

    def test_fetch_ip_with_cloned_mac(self):
        """Пробуем получить ip с opt82 от одной учётки, но маком от другой.
           Должны не вестись на такое.
        """
        self.test_normal_new_session()

        # Делаем ip для второй учётки
        r = self._send_request_acct(
            cid='0004008B0002',
            arid='0006131314151717',
            ip='10.152.65.17',
            mac='1c:c0:4d:95:d0:36',
        )
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(r.data)

        # На первой учётке ip 10.152.64.6
        leases4customer1 = self._get_ip_leases()
        self.assertEqual(len(leases4customer1), 1)

        # На второй учётке ip 10.152.65.17
        leases4customer2 = self._get_ip_leases(customer_id=self.full_customer2.customer.pk)
        self.assertEqual(len(leases4customer2), 1)

        # Пробуем получить первый ip
        r = self._send_request_auth(
            cid='0004008B0002',
            arid='0006121314151617',
            mac='1c:c0:4d:95:d0:30'
        )
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['Framed-IP-Address'], '10.152.64.6')

        # Пробуем получить второй ip
        r = self._send_request_auth(
            cid='0004008B0002',
            arid='0006131314151717',
            mac='1c:c0:4d:95:d0:36'
        )
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['Framed-IP-Address'], '10.152.65.17')

        # Пробуем получить ip с первой учётки, с маком абонента от второй
        r = self._send_request_auth(
            cid='0004008B0002',
            arid='0006121314151617',
            mac='1c:c0:4d:95:d0:36'
        )
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['User-Password'], 'SERVICE-INET(11000000,2062500,11000000,2062500)')
        # т.к. мак отличается, то говорим что на учётке нет подходящего ip, надо подбирать новый
        self.assertIsNone(d.get('Framed-IP-Address'))

        # Пробуем получить ip со второй учётки, с маком абонента от первой
        r = self._send_request_auth(
            cid='0004008B0002',
            arid='0006131314151717',
            mac='1c:c0:4d:95:d0:30'
        )
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['User-Password'], 'SERVICE-INET(11000000,2062500,11000000,2062500)')
        # т.к. мак отличается, то говорим что на учётке нет подходящего ip, надо подбирать новый
        self.assertIsNone(d.get('Framed-IP-Address'))

    #def test_profile_with_opt82_and_bad_vid(self):
    #    """Если по opt82 находим учётку, но vid не существует.
    #       Пока не делаю, т.к. в билинге не должно быть информации по пулам,
    #       она должна быть в модуле который занимается выдачей ip.
    #    """
    #    pass



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


class Option82TestCase(SimpleTestCase):
    def test_parse_opt82_ok(self):
        circuit_id = b"\x00\x04\x00\x98\x00\x05"
        rem_id = b"\x00\x06\xec\x22\x80\x7f\xad\xb8"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "ec:22:80:7f:ad:b8")
        self.assertEqual(port, 5)

    def test_parse_opt82_ok2(self):
        circuit_id = b"\x00\x74\x00\x07\x1d"
        rem_id = b"\x1c\x87\x79\x12\xe6\x1a"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 29)

    def test_parse_opt82_long_data(self):
        circuit_id = b"\x00\x74\x00\xff\x1d\xff\x01"
        rem_id = b"\xff\x12\x1c\x87\x79\x12\xe6\x1a"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "1c:87:79:12:e6:1a")
        self.assertEqual(port, 1)

    def test_parse_opt82_short_data(self):
        circuit_id = b"\x00\x74\x00\xff"
        rem_id = b"\x1c\x87\x79"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertIsNone(mac)
        self.assertEqual(port, 255)

    def test_parse_opt82_ok_zte(self):
        circuit_id = b"\x5a\x54\x45\x47\x43\x30\x32\x38\x38\x45\x37\x30"
        rem_id = b"\x34\x35\x3a\x34\x37\x3a\x63\x30\x3a\x32\x38\x3a\x38\x65\x3a\x37\x30"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c0:28:8e:70")
        self.assertEqual(port, 0)

    def test_parse_opt82_ok_zte2(self):
        circuit_id = b"\x5a\x54\x45\x47\x43\x34\x30\x32\x35\x33\x42\x33"
        rem_id = b"\x34\x35\x3a\x34\x37\x3a\x63\x34\x3a\x32\x3a\x35\x33\x3a\x62\x33"
        mac, port = parse_opt82(remote_id=rem_id, circuit_id=circuit_id)
        self.assertEqual(mac, "45:47:c4:2:53:b3")
        self.assertEqual(port, 0)


class CreateLeaseWAutoPoolNSessionTestCase(TestCase):
    def setUp(self):
        signals.post_save.disconnect()
        signals.post_delete.disconnect()
        signals.pre_save.disconnect()
        signals.pre_delete.disconnect()

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

    def test_normal(self):
        """Просто тыкаем, отработает-ли вообще"""
        is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
            ip='10.152.16.37',
            mac='18:c0:4d:51:de:e3',
            customer_id=self.full_customer.customer.pk,
            radius_uname='50d4.f794.d535-ae0:1011-139',
            radius_unique_id='02e65fad-07c3-20d8-9149-a66eadebd562'
        )
        self.assertTrue(is_created)

        sessions_qs = CustomerRadiusSession.objects.all()
        leases_qs = CustomerIpLeaseModel.objects.all()

        self.assertEqual(sessions_qs.count(), 1)
        self.assertEqual(leases_qs.count(), 1)

        customer = self.full_customer.customer

        lease = leases_qs.first()
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.152.16.37')
        self.assertIsNone(lease.pool)
        self.assertEqual(lease.customer_id, customer.pk)
        self.assertEqual(lease.mac_address, '18:c0:4d:51:de:e3')
        self.assertTrue(lease.is_dynamic)
        self.assertIsNotNone(lease.last_update)

        session = sessions_qs.first()
        self.assertIsNotNone(session)
        self.assertEqual(session.customer_id, customer.pk)
        self.assertEqual(session.radius_username, '50d4.f794.d535-ae0:1011-139')
        self.assertEqual(session.ip_lease, lease)
        self.assertEqual(str(session.session_id), '02e65fad-07c3-20d8-9149-a66eadebd562')
        self.assertIsNone(session.session_duration)
        self.assertEqual(session.input_octets, 0)
        self.assertEqual(session.output_octets, 0)
        self.assertEqual(session.input_packets, 0)
        self.assertEqual(session.output_packets, 0)
        self.assertFalse(session.closed)

    def test_check_for_exist_session(self):
        """Проверяем что при первом обращении сессия создастся,
           а при повтормном, с теми же credentials просто вернётся
        """
        is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
            ip='10.152.16.37',
            mac='18:c0:4d:51:de:e3',
            customer_id=self.full_customer.customer.pk,
            radius_uname='50d4.f794.d535-ae0:1011-139',
            radius_unique_id='02e65fad-07c3-20d8-9149-a66eadebd562'
        )
        self.assertTrue(is_created)
        is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
            ip='10.152.16.37',
            mac='18:c0:4d:51:de:e3',
            customer_id=self.full_customer.customer.pk,
            radius_uname='50d4.f794.d535-ae0:1011-139',
            radius_unique_id='02e65fad-07c3-20d8-9149-a66eadebd562'
        )
        self.assertFalse(is_created)

    def test_creating_2_sessions_on_profile(self):
        """Пробуем создать 2 разные сессии на учётку."""
        is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
            ip='10.152.16.37',
            mac='18:c0:4d:51:de:e3',
            customer_id=self.full_customer.customer.pk,
            radius_uname='50d4.f794.d535-ae0:1011-139',
            radius_unique_id='02e65fad-07c3-20d8-9149-a66eadebd562'
        )
        self.assertTrue(is_created)

        is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
            ip='10.152.16.33',
            mac='18:c0:4d:51:de:e4',
            customer_id=self.full_customer.customer.pk,
            radius_uname='50d4.f794.d535-ae0:1011-149',
            radius_unique_id='02e65fad-07c3-20d8-9149-a66eadebd563'
        )
        self.assertTrue(is_created)

        sessions_qs = CustomerRadiusSession.objects.all()
        leases_qs = CustomerIpLeaseModel.objects.all()
        self.assertEqual(sessions_qs.count(), 2)
        self.assertEqual(leases_qs.count(), 2)

    #def test_one_session_constraint(self):
    #    """Пробуем создать 2 сессии на одну аренду ip.
    #       Там есть constraint о том что аренда может содеражть только одну сессию.
    #    """
    #    from django.forms.models import model_to_dict
    #    from time import sleep
    #    is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
    #        ip='10.152.16.37',
    #        mac='18:c0:4d:51:de:e3',
    #        customer_id=self.full_customer.customer.pk,
    #        radius_uname='50d4.f794.d535-ae0:1011-139',
    #        radius_unique_id='02e65fad-07c3-20d8-9149-a66eadebd562'
    #    )
    #    self.assertTrue(is_created)

    #    sessions_qs = CustomerRadiusSession.objects.all()
    #    leases_qs = CustomerIpLeaseModel.objects.all()

    #    for ses in sessions_qs:
    #        print('Ses1', model_to_dict(ses))
    #    for lease in leases_qs:
    #        print('Lease1', model_to_dict(lease))

    #    is_created = CustomerRadiusSession.create_lease_w_auto_pool_n_session(
    #        ip='10.152.16.37',
    #        mac='18:c0:4d:51:de:e3',
    #        customer_id=self.full_customer.customer.pk,
    #        radius_uname='50d4.f794.d535-ae0:1011-149',
    #        radius_unique_id='02e65fad-07c3-20d8-9149-a66eadebd563'
    #    )
    #    #  self.assertTrue(is_created)

    #    sessions_qs = CustomerRadiusSession.objects.all()
    #    leases_qs = CustomerIpLeaseModel.objects.all()

    #    for ses in sessions_qs:
    #        print('Ses2', model_to_dict(ses))
    #    for lease in leases_qs:
    #        print('Lease2', model_to_dict(lease))

