from django.test import TestCase

from networks.models import VlanIf, NetworkIpPool, NetworkIpPoolKind
from networks.tests import LeaseCommitAddUpdateTestCase
from radiusapp.models import UserSession


class FetchSubscriberLease(TestCase):
    def setUp(self):
        vlan1 = VlanIf.objects.create(
            title='Vlan for customer tests',
            vid=12
        )
        self.pool_guest = NetworkIpPool.objects.create(
            network='10.255.0.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_GUEST.value,
            description='Guest ip pool',
            ip_start='10.255.0.2',
            ip_end='10.255.0.254',
            vlan_if=None,
            gateway='192.168.0.1',
            is_dynamic=True
        )
        self.pool_dynamic = NetworkIpPool.objects.create(
            network='192.168.0.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET.value,
            description='Dynamic customer test',
            ip_start='192.168.0.2',
            ip_end='192.168.0.254',
            vlan_if=vlan1,
            gateway='192.168.0.1',
            is_dynamic=True
        )
        self.pool_static = NetworkIpPool.objects.create(
            network='192.168.1.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET.value,
            description='Static customer test',
            ip_start='192.168.1.2',
            ip_end='192.168.1.4',
            vlan_if=vlan1,
            gateway='192.168.1.1',
            is_dynamic=False
        )
        self.vlan1 = vlan1
        LeaseCommitAddUpdateTestCase.setUp(self)

        self.pool_guest.groups.add(self.group)
        self.pool_dynamic.groups.add(self.group)
        self.pool_static.groups.add(self.group)

    def test_normal_fetch(self):
        res = UserSession.objects.fetch_subscriber_lease(
            customer_mac='aa:bb:cc:dd:ee:ff',
            device_mac='12:13:14:15:16:17',
            device_port=2,
            is_dynamic=True,
            vid=12
        )
        print('RES:', res)
        self.assertIsNotNone(res)
        self.assertEqual(res['ip_addr'], '192.168.0.2')
        self.assertEqual(res['pool_id'], self.pool_dynamic.pk)
        self.assertEqual(res['customer_mac'], 'aa:bb:cc:dd:ee:ff')
        self.assertEqual(res['customer_id'], self.customer.pk)
        self.assertTrue(res['is_dynamic'])
        self.assertTrue(res['is_assigned'])
