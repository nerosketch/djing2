from django.test import TestCase

from customers.models import Customer
from networks.models import CustomerIpLeaseModel, NetworkIpPool, NetworkIpPoolKind
from customers.tests.get_user_credentials_by_ip import BaseServiceTestCase


class FetchSubscriberStaticLeaseTestCase(TestCase):
    def setUp(self):
        # Initialize customers instances
        BaseServiceTestCase.setUp(self)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

        # customer for tests
        custo2 = Customer.objects.create_user(
            telephone='+79782345679',
            username='custo2',
            password='passw',
            group=self.group,
            device=self.device_onu
        )
        custo2.refresh_from_db()
        self.customer2 = custo2

        self.ippool = NetworkIpPool.objects.create(
            network='10.11.12.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.11.12.2',
            ip_end='10.11.12.254',
            # vlan_if=vlan,
            gateway='10.11.12.1',
            is_dynamic=False
        )
        self.ippool.groups.add(self.group)

    def test_is_ok(self):
        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.pool, self.ippool)
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)

    def test_multiple_fetch(self):
        for n in range(4):
            lease = CustomerIpLeaseModel.fetch_subscriber_lease(
                customer_mac='1:2:3:4:5:7',
                device_mac='12:13:14:15:16:17',
                device_port=2,
                is_dynamic=False
            )
            self.assertIsNotNone(lease)
            self.assertEqual(lease.ip_address, '10.11.12.2')
            self.assertEqual(lease.pool, self.ippool)
            self.assertEqual(lease.customer, self.customer)
            self.assertFalse(lease.is_dynamic)

    def test_different_mac(self):
        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)
        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:7',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)
        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:8',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)

    def test_multiple_customers(self):
        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)
        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:8',
            device_mac='11:13:14:15:16:18',
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.3')
        self.assertEqual(lease.customer, self.customer2)
        self.assertFalse(lease.is_dynamic)

    def test_ident_mac(self):
        """
        What if two different customers have the same mac addr
        """
        for n in range(4):
            lease = CustomerIpLeaseModel.fetch_subscriber_lease(
                customer_mac='1:2:3:4:5:6',
                device_mac='12:13:14:15:16:17',
                device_port=2,
                is_dynamic=False
            )
            self.assertIsNotNone(lease)
            self.assertEqual(lease.ip_address, '10.11.12.2')
            self.assertEqual(lease.customer, self.customer)
            self.assertFalse(lease.is_dynamic)
            lease = CustomerIpLeaseModel.fetch_subscriber_lease(
                customer_mac='1:2:3:4:5:6',
                device_mac='11:13:14:15:16:18',
                is_dynamic=False
            )
            self.assertIsNotNone(lease)
            self.assertEqual(lease.ip_address, '10.11.12.3')
            self.assertEqual(lease.customer, self.customer2)
            self.assertFalse(lease.is_dynamic)

    def test_change_subnet(self):
        """
        What if group membership for ip pool is changed
        :return:
        """
        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)

        ippool2 = NetworkIpPool.objects.create(
            network='10.10.11.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.10.11.2',
            ip_end='10.10.11.254',
            gateway='10.10.11.1',
            is_dynamic=False
        )
        self.ippool.groups.remove(self.group)
        ippool2.groups.add(self.group)

        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.10.11.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)

        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:7',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.10.11.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)

        lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=False
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.10.11.2')
        self.assertEqual(lease.customer, self.customer)
        self.assertFalse(lease.is_dynamic)
