from django.test import TestCase
from netaddr import EUI

from customers.models import Customer
from networks.models import CustomerIpLeaseModel, NetworkIpPool
from services.tests.get_user_credentials_by_ip import BaseServiceTestCase


class FetchSubscriberDynamicLeaseTestCase(TestCase):
    def setUp(self):
        # Initialize customers instances
        BaseServiceTestCase.setUp(self)

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
            kind=NetworkIpPool.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.11.12.2',
            ip_end='10.11.12.254',
            # vlan_if=vlan,
            gateway='10.11.12.1'
        )
        self.ippool.groups.add(self.group)

    def test_is_ok(self):
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.pool, self.ippool)
        self.assertEqual(lease.customer, self.customer)
        self.assertEqual(lease.mac_address, EUI('1:2:3:4:5:6'))
        self.assertTrue(lease.is_dynamic)

    def test_multiple_fetch(self):
        for n in range(4):
            lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
                customer_mac='1:2:3:4:5:7',
                device_mac='12:13:14:15:16:17',
                device_port=2,
            )
            self.assertIsNotNone(lease)
            self.assertEqual(lease.ip_address, '10.11.12.2')
            self.assertEqual(lease.customer, self.customer)

    def test_different_mac(self):
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:7',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.3')
        self.assertEqual(lease.customer, self.customer)
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:8',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.4')
        self.assertEqual(lease.customer, self.customer)

    def test_multiple_customers(self):
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:8',
            device_mac='11:13:14:15:16:18'
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.3')
        self.assertEqual(lease.customer, self.customer2)

    def test_ident_mac(self):
        """
        What if two different customers have the same mac addr
        """
        for n in range(4):
            lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
                customer_mac='1:2:3:4:5:6',
                device_mac='12:13:14:15:16:17',
                device_port=2,
            )
            self.assertIsNotNone(lease)
            self.assertEqual(lease.ip_address, '10.11.12.2')
            self.assertEqual(lease.customer, self.customer)
            lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
                customer_mac='1:2:3:4:5:6',
                device_mac='11:13:14:15:16:18'
            )
            self.assertIsNotNone(lease)
            self.assertEqual(lease.ip_address, '10.11.12.3')
            self.assertEqual(lease.customer, self.customer2)

    def test_change_subnet(self):
        """
        What if group membership for ip pool is changed
        :return:
        """
        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.11.12.2')
        self.assertEqual(lease.customer, self.customer)

        ippool2 = NetworkIpPool.objects.create(
            network='10.10.11.0/24',
            kind=NetworkIpPool.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.10.11.2',
            ip_end='10.10.11.254',
            gateway='10.10.11.1'
        )
        self.ippool.groups.remove(self.group)
        ippool2.groups.add(self.group)

        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.10.11.2')
        self.assertEqual(lease.customer, self.customer)

        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:7',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.10.11.3')
        self.assertEqual(lease.customer, self.customer)

        lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(lease)
        self.assertEqual(lease.ip_address, '10.10.11.2')
        self.assertEqual(lease.customer, self.customer)
