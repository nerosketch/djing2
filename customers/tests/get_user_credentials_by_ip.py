from django.test import TestCase

from customers.models import Customer, CustomerService
from devices.tests import DeviceTestCase
from networks.models import CustomerIpLeaseModel, NetworkIpPool, NetworkIpPoolKind
from services.models import Service
from services.custom_logic import SERVICE_CHOICE_DEFAULT
from .customer import CustomAPITestCase


class BaseServiceTestCase(TestCase):
    def setUp(self):
        # Initialize customers instances
        CustomAPITestCase.setUp(self)

        # Initialize devices instances
        DeviceTestCase.setUp(self)

        self.service = Service.objects.create(
            title='test',
            descr='test',
            speed_in=10.0,
            speed_out=10.0,
            cost=10.0,
            calc_type=SERVICE_CHOICE_DEFAULT
        )


class GetUserCredentialsByIpTestCase(BaseServiceTestCase):
    def setUp(self):
        super().setUp()
        self.ippool = NetworkIpPool.objects.create(
            network='10.11.12.0/24',
            kind=NetworkIpPoolKind.NETWORK_KIND_INTERNET.value,
            description='test',
            ip_start='10.11.12.2',
            ip_end='10.11.12.254',
            # vlan_if=vlan,
            gateway='10.11.12.1',
            is_dynamic=True
        )
        self.ippool.groups.add(self.group)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

        self.lease = CustomerIpLeaseModel.objects.create(
            ip_address='10.11.12.2',
            mac_address='1:2:3:4:5:6',
            pool=self.ippool,
            customer=self.customer,
            is_dynamic=True
        )
        self.assertIsNotNone(self.lease)
        # lease must be contain ip_address=10.11.12.2'

    def test_get_user_credentials_by_ip(self):
        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr='10.11.12.2'
        )
        self.assertIsNotNone(customer_service)
        self.assertEqual(customer_service.service.speed_in, 10.0)
        self.assertEqual(customer_service.service.speed_out, 10.0)
        self.assertEqual(customer_service.service.speed_burst, 1)
        self.assertEqual(customer_service.service.cost, 10.0)
        self.assertEqual(customer_service.service.calc_type, SERVICE_CHOICE_DEFAULT)

    def test_not_exists_lease(self):
        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr='10.11.12.12'
        )
        self.assertIsNone(customer_service)

    def test_if_ip_is_none(self):
        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr=None
        )
        self.assertIsNone(customer_service)

    def test_if_ip_is_bad(self):
        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr='10.11.12.12.13'
        )
        self.assertIsNone(customer_service)

    def test_customer_disabled(self):
        self.customer.is_active = False
        self.customer.save(update_fields=['is_active'])
        # self.customer.refresh_from_db()
        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr='10.11.12.2'
        )
        self.assertIsNone(customer_service)

    def test_customer_does_not_have_service(self):
        self.customer.stop_service(self.customer)
        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr='10.11.12.2'
        )
        self.assertIsNone(customer_service)

    def test_customer_with_onu_device(self):
        # customer for tests
        customer_onu = Customer.objects.create_user(
            telephone='+79782345679',
            username='custo_onu',
            password='passww'
        )
        customer_onu.device = self.device_onu
        customer_onu.add_balance(self.admin, 10000, 'test')
        customer_onu.save()
        customer_onu.refresh_from_db()
        customer_onu.pick_service(self.service, customer_onu)
        self.customer_onu = customer_onu

        self.lease = CustomerIpLeaseModel.objects.create(
            ip_address='10.11.12.3',
            mac_address='1:2:3:4:5:6',
            pool=self.ippool,
            customer=customer_onu,
            is_dynamic=True
        )
        self.assertIsNotNone(self.lease)
        # lease must be contain ip_address=10.11.12.3'

        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr='10.11.12.3',
        )
        self.assertIsNotNone(customer_service)
        self.assertEqual(customer_service.service.speed_in, 10.0)
        self.assertEqual(customer_service.service.speed_out, 10.0)
        self.assertEqual(customer_service.service.speed_burst, 1)
        self.assertEqual(customer_service.service.cost, 10.0)
        self.assertEqual(customer_service.service.calc_type, SERVICE_CHOICE_DEFAULT)
