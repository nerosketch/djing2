from collections import OrderedDict

from django.test import override_settings

from customers.models import Customer
from customers.tests.customer import CustomAPITestCase
from djing2.lib import calc_hash
from networks.models import NetworkIpPool, NetworkIpPoolKind, CustomerIpLeaseLog
from customers.tests.get_user_credentials_by_ip import BaseServiceTestCase


@override_settings(API_AUTH_SUBNET="127.0.0.0/8")
class LeaseCommitAddUpdateTestCase(CustomAPITestCase):
    def setUp(self):
        # Initialize customers instances
        BaseServiceTestCase.setUp(self)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, "test")
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

        # customer for tests
        custo2 = Customer.objects.create_user(
            telephone="+79782345679", username="custo2", password="passw", group=self.group, device=self.device_onu
        )
        custo2.refresh_from_db()
        self.customer2 = custo2

        self.ippool = NetworkIpPool.objects.create(
            network="10.11.12.0/24",
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            description="test",
            ip_start="10.11.12.2",
            ip_end="10.11.12.254",
            # vlan_if=vlan,
            gateway="10.11.12.1",
            is_dynamic=True,
        )
        self.ippool.groups.add(self.group)

        self.client.logout()

    def _make_event_request(
        self, client_ip: str, client_mac: str, switch_mac: str, switch_port: int, cmd: str, status_code: int = 200
    ):
        request_data = OrderedDict(
            {
                "client_ip": client_ip,
                "client_mac": client_mac,
                "switch_mac": switch_mac,
                "switch_port": str(switch_port),
                "cmd": cmd,
            }
        )
        hdrs = {"Api-Auth-Sign": calc_hash(request_data)}
        r = self.client.get(
            "/api/networks/dhcp_lever/", data=request_data, SERVER_NAME="example.com", format="json", **hdrs
        )
        self.assertEqual(r.status_code, status_code, msg=r.content)
        return r.data

    # @staticmethod
    # def _sleep_db():
    #     with connection.cursor() as cur:
    #         cur.execute("select pg_sleep(3);")
    #         r = cur.fetchone()
    #     return r

    @override_settings(API_AUTH_SECRET="sdfsdf")
    def test_ok(self):
        r = self._make_event_request("10.11.12.55", "12:13:14:15:16:15", "12:13:14:15:16:17", 2, "commit")
        self.assertDictEqual(r, {"text": "Assigned 10.11.12.55"})

    @override_settings(API_AUTH_SECRET="sdfsdf")
    def test_update_last_update_time(self):
        r = self._make_event_request("10.11.12.60", "12:13:14:15:16:20", "12:13:14:15:16:17", 2, "commit")
        self.assertDictEqual(r, {"text": "Assigned 10.11.12.60"})
        r = self._make_event_request("10.11.12.60", "12:13:14:15:16:20", "12:13:14:15:16:17", 2, "commit")
        self.assertDictEqual(r, {"text": "Assigned null"})

    def test_ip_lease_logging_new_lease(self):
        r = self._make_event_request("10.11.12.60", "12:13:14:15:16:20", "12:13:14:15:16:17", 2, "commit")
        self.assertDictEqual(r, {"text": "Assigned 10.11.12.60"})
        logs = CustomerIpLeaseLog.objects.filter(
            customer=self.customer,
        )
        self.assertTrue(logs.exists())
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.customer, self.customer)
        self.assertEqual(log.ip_address, "10.11.12.60")
        self.assertIsNone(log.end_use_time)
        self.assertEqual(log.mac_address, "12:13:14:15:16:20")
        self.assertTrue(log.is_dynamic)

    def test_ip_lease_logging_repeated_lease(self):
        self._make_event_request("10.11.12.60", "12:13:14:15:16:20", "12:13:14:15:16:17", 2, "commit")
        r = self._make_event_request("10.11.12.60", "12:13:14:15:16:20", "12:13:14:15:16:17", 2, "commit")
        self.assertDictEqual(r, {"text": "Assigned null"})
        logs = CustomerIpLeaseLog.objects.filter(customer=self.customer)
        self.assertTrue(logs.exists())
        self.assertEqual(logs.count(), 1)

    def test_ip_lease_logging_old_lease_2_logs(self):
        self._make_event_request("10.11.12.60", "12:13:14:15:16:20", "12:13:14:15:16:17", 2, "commit")
        self._make_event_request("10.11.12.61", "12:13:14:15:16:21", "12:13:14:15:16:17", 2, "commit")
        logs = CustomerIpLeaseLog.objects.filter(
            customer=self.customer,
        )
        self.assertTrue(logs.exists())
        self.assertEqual(logs.count(), 2)

    def test_ip_lease_log_time(self):
        # device_switch, customer
        self._make_event_request("10.11.12.60", "12:13:14:15:16:20", "12:13:14:15:16:17", 2, "commit")

        self._make_event_request("10.11.12.60", "12:13:14:15:16:21", "11:13:14:15:16:18", 0, "commit")

        logs = CustomerIpLeaseLog.objects.filter(
            ip_address="10.11.12.60",
        )
        self.assertTrue(logs.exists())
        self.assertEqual(logs.count(), 2)
        log_customer1 = logs.filter(customer=self.customer).first()
        self.assertIsNotNone(log_customer1)
        self.assertEqual(log_customer1.customer, self.customer)
        self.assertEqual(log_customer1.ip_address, "10.11.12.60")
        self.assertEqual(log_customer1.mac_address, "12:13:14:15:16:20")
        self.assertIsNotNone(log_customer1.lease_time)
        self.assertIsNotNone(log_customer1.last_update)
        self.assertIsNotNone(log_customer1.event_time)
        self.assertIsNotNone(log_customer1.end_use_time)
        # self.assertEqual(log_customer1.end_use_time, log_customer1.event_time + timedelta(seconds=2))

        log_customer2 = logs.filter(customer=self.customer2).first()
        self.assertIsNotNone(log_customer2)
        self.assertEqual(log_customer2.customer, self.customer2)
        self.assertEqual(log_customer2.ip_address, "10.11.12.60")
        self.assertEqual(log_customer2.mac_address, "12:13:14:15:16:21")
        self.assertIsNotNone(log_customer2.lease_time)
        self.assertIsNotNone(log_customer2.last_update)
        self.assertIsNotNone(log_customer2.event_time)
        self.assertIsNone(log_customer2.end_use_time)
