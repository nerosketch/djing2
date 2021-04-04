from django.db import DataError
from django.test import TestCase

from networks.models import VlanIf, NetworkIpPool, NetworkIpPoolKind, CustomerIpLeaseModel
from networks.tests import LeaseCommitAddUpdateTestCase
from radiusapp.models import CustomerRadiusSession


class FetchSubscriberLease(TestCase):
    def setUp(self):
        vlan1 = VlanIf.objects.create(title="Vlan for customer tests", vid=12)
        # self.pool_guest = NetworkIpPool.objects.create(
        #     network='10.255.0.0/24',
        #     kind=NetworkIpPoolKind.NETWORK_KIND_GUEST.value,
        #     description='Guest ip pool',
        #     ip_start='10.255.0.2',
        #     ip_end='10.255.0.254',
        #     vlan_if=None,
        #     gateway='192.168.0.1',
        #     is_dynamic=True
        # )
        self.pool_dynamic = NetworkIpPool.objects.create(
            network="192.168.0.0/24",
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET.value,
            description="Dynamic customer test",
            ip_start="192.168.0.2",
            ip_end="192.168.0.254",
            vlan_if=vlan1,
            gateway="192.168.0.1",
            is_dynamic=True,
        )
        # self.pool_static = NetworkIpPool.objects.create(
        #     network='192.168.1.0/24',
        #     kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET.value,
        #     description='Static customer test',
        #     ip_start='192.168.1.2',
        #     ip_end='192.168.1.4',
        #     vlan_if=vlan1,
        #     gateway='192.168.1.1',
        #     is_dynamic=False
        # )
        self.vlan1 = vlan1
        LeaseCommitAddUpdateTestCase.setUp(self)

        # self.pool_guest.groups.add(self.group)
        self.pool_dynamic.groups.add(self.group)
        # self.pool_static.groups.add(self.group)

        NetworkIpPool.objects.filter(pk=self.ippool.pk).delete()
        del self.ippool

    def test_normal_fetch(self):
        res = CustomerRadiusSession.objects.fetch_subscriber_lease(
            customer_mac="aa:bb:cc:dd:ee:ff",
            customer_id=self.customer.pk,
            customer_group=self.customer.group_id,
            is_dynamic=True,
            vid=12,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.ip_addr, "192.168.0.2")
        self.assertEqual(res.pool_id, self.pool_dynamic.pk)
        self.assertEqual(res.customer_mac, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(res.customer_id, self.customer.pk)
        self.assertTrue(res.is_dynamic)
        self.assertTrue(res.is_assigned)

    def test_static_normal_fetch(self):
        res = CustomerRadiusSession.objects.fetch_subscriber_lease(
            customer_mac="aa:bb:cc:dd:ee:ff",
            customer_id=self.customer.pk,
            customer_group=self.customer.group_id,
            is_dynamic=False,
            vid=12,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
        )
        self.assertIsNone(res)

    def test_two_dynamic_fetch(self):
        self.test_normal_fetch()
        res = CustomerRadiusSession.objects.fetch_subscriber_lease(
            customer_mac="1a:b6:4c:cd:e3:fe",
            customer_id=self.customer.pk,
            customer_group=self.customer.group_id,
            is_dynamic=True,
            vid=12,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.ip_addr, "192.168.0.3")
        self.assertEqual(res.pool_id, self.pool_dynamic.pk)
        self.assertEqual(res.customer_mac, "1a:b6:4c:cd:e3:fe")
        self.assertEqual(res.customer_id, self.customer.pk)
        self.assertTrue(res.is_dynamic)
        self.assertTrue(res.is_assigned)

        leases_count = CustomerIpLeaseModel.objects.filter(customer=self.customer).count()
        self.assertEqual(leases_count, 2)

    def test_bad_data(self):
        with self.assertRaises(DataError):
            CustomerRadiusSession.objects.fetch_subscriber_lease(
                customer_mac="1-2e0-qedq0jdwqwoiked",
                customer_id=self.customer.pk,
                customer_group=self.customer.group_id,
                is_dynamic=True,
                vid=12,
                pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            )

    def test_empty_vid(self):
        res = CustomerRadiusSession.objects.fetch_subscriber_lease(
            customer_mac="aa:bb:cc:dd:ee:ff",
            customer_id=self.customer.pk,
            customer_group=self.customer.group_id,
            is_dynamic=True,
            vid=None,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.ip_addr, "192.168.0.2")
        self.assertEqual(res.pool_id, self.pool_dynamic.pk)
        self.assertEqual(res.customer_mac, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(res.customer_id, self.customer.pk)
        self.assertTrue(res.is_dynamic)
        self.assertTrue(res.is_assigned)

    def test_multiple_fetch(self):
        res = CustomerRadiusSession.objects.fetch_subscriber_lease(
            customer_mac="aa:bb:cc:dd:ee:ff",
            customer_id=self.customer.pk,
            customer_group=self.customer.group_id,
            is_dynamic=True,
            vid=12,
            pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.ip_addr, "192.168.0.2")
        self.assertEqual(res.pool_id, self.pool_dynamic.pk)
        self.assertEqual(res.customer_mac, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(res.customer_id, self.customer.pk)
        self.assertTrue(res.is_dynamic)
        self.assertTrue(res.is_assigned)
        for n in range(4):
            res = CustomerRadiusSession.objects.fetch_subscriber_lease(
                customer_mac="aa:bb:cc:dd:ee:ff",
                customer_id=self.customer.pk,
                customer_group=self.customer.group_id,
                is_dynamic=True,
                vid=12,
                pool_kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET,
            )
            self.assertIsNotNone(res)
            self.assertEqual(res.ip_addr, "192.168.0.2")
            self.assertEqual(res.pool_id, self.pool_dynamic.pk)
            self.assertEqual(res.customer_mac, "aa:bb:cc:dd:ee:ff")
            self.assertEqual(res.customer_id, self.customer.pk)
            self.assertTrue(res.is_dynamic)
            self.assertFalse(res.is_assigned)
