from django.test import TestCase
from networks.models import NetworkIpPool, VlanIf, CustomerIpLeaseModel
from customers.tests import CustomAPITestCase


class IpPoolTestCase(TestCase):

    def setUp(self):
        self.vlan1 = VlanIf.objects.create(
            title='Test vlan 1',
            vid=12,
        )

        self.pool1 = NetworkIpPool.objects.create(
            network='192.168.0.0/24',
            kind=NetworkIpPool.NETWORK_KIND_GUEST,
            description='TEST1',
            ip_start='192.168.0.2',
            ip_end='192.168.0.254',
            vlan_if=self.vlan1,
            gateway='192.168.0.1'
        )
        self.pool_small = NetworkIpPool.objects.create(
            network='192.168.1.0/24',
            kind=NetworkIpPool.NETWORK_KIND_DEVICES,
            description='TEST2',
            ip_start='192.168.1.2',
            ip_end='192.168.1.4',
            vlan_if=self.vlan1,
            gateway='192.168.1.1'
        )

        # Initialize customers instances
        CustomAPITestCase.setUp(self)

    def test_get_free_ip_from_empty_leases(self):
        free_ip = str(self.pool1.get_free_ip())
        self.assertEqual(free_ip, '192.168.0.2')

    def test_get_free_ip_from_filled_leases(self):
        # Fill leases
        CustomerIpLeaseModel.objects.bulk_create(
            objs=(CustomerIpLeaseModel(
                ip_address='192.168.0.%d' % ip,
                pool=self.pool1,
                customer=self.customer,
                mac_address='11:7b:41:46:d3:%.2x' % ip
            ) for ip in range(2, 250))
        )
        free_ip = str(self.pool1.get_free_ip())
        self.assertEqual(free_ip, '192.168.0.250')

    def test_get_free_ip_from_full_leases(self):
        # Full fill leases
        CustomerIpLeaseModel.objects.bulk_create(
            objs=(CustomerIpLeaseModel(
                ip_address='192.168.0.%d' % ip,
                pool=self.pool1,
                customer=self.customer,
                mac_address='11:7b:41:46:d3:%.2x' % ip
            ) for ip in range(2, 255))
        )
        free_ip = self.pool1.get_free_ip()
        self.assertIsNone(free_ip)

    def test_get_free_ip_from_beetween_leases(self):
        # Full fill leases
        CustomerIpLeaseModel.objects.bulk_create(
            objs=(CustomerIpLeaseModel(
                ip_address='192.168.0.%d' % ip,
                pool=self.pool1,
                customer=self.customer,
                mac_address='11:7b:41:46:d3:%.2x' % ip
            ) for ip in range(2, 255))
        )
        # Delete from some lease
        CustomerIpLeaseModel.objects.filter(ip_address='192.168.0.156').delete()
        free_ip = str(self.pool1.get_free_ip())
        self.assertEqual(free_ip, '192.168.0.156')

    def test_for_busy_pool(self):
        CustomerIpLeaseModel.objects.bulk_create(
            objs=(CustomerIpLeaseModel(
                ip_address='192.168.1.%d' % ip,
                pool=self.pool_small,
                customer=self.customer,
                mac_address='11:7b:41:46:d3:%.2x' % ip
            ) for ip in range(2, 7))
        )
        free_ip = self.pool_small.get_free_ip()
        self.assertIsNone(free_ip)
