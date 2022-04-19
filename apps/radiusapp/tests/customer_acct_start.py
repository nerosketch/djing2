from typing import Optional
from django.test import override_settings
from django.db.models import signals
from rest_framework import status
from rest_framework.test import APITestCase
from profiles.models import UserProfile
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from networks.models import (
    VlanIf, NetworkIpPool,
    NetworkIpPoolKind
)
from devices.device_config.switch.dlink.dgs_1100_10me import DEVICE_UNIQUE_CODE as Dlink_dgs1100_10me_code
from .customer_auth import radius_api_request_auth
from ._create_full_customer import create_full_customer


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
        # Создаём динамический ip в vlan 12, 10.152.64.6
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
            mac='1c:c0:4d:95:d0:30'
        )
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(d['Framed-IP-Address'], '10.152.65.16')

        # Пробуем получить динамичекий ip vlan12
        r = self._send_request_auth(
            #  vlan_id=12,
            cid='0004008B0002',
            arid='0006121314151617',
            mac='1c:c0:4d:95:d0:38'
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

