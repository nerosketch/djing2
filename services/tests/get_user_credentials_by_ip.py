from django.test import TestCase

from customers.models import Customer
from customers.tests import CustomAPITestCase
from devices.tests import DeviceTestCase
from networks.models import CustomerIpLeaseModel, NetworkIpPool
from services.models import Service, SERVICE_CHOICE_DEFAULT


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
            kind=NetworkIpPool.NETWORK_KIND_INTERNET,
            description='test',
            ip_start='10.11.12.2',
            ip_end='10.11.12.254',
            # vlan_if=vlan,
            gateway='10.11.12.1'
        )
        self.ippool.groups.add(self.group)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

        self.lease = CustomerIpLeaseModel.fetch_subscriber_dynamic_lease(
            customer_mac='1:2:3:4:5:6',
            device_mac='12:13:14:15:16:17',
            device_port=2,
        )
        self.assertIsNotNone(self.lease)
        # lease must be contain ip_address=10.11.12.2'

    def test_get_user_credentials_by_ip(self):
        customer_service = Service.get_user_credentials_by_ip(
            ip_addr='10.11.12.2'
        )
        self.assertIsNotNone(customer_service)
        self.assertEqual(customer_service.speed_in, 10.0)
        self.assertEqual(customer_service.speed_out, 10.0)
        self.assertEqual(customer_service.speed_burst, 1)
        self.assertEqual(customer_service.cost, 10.0)
        self.assertEqual(customer_service.calc_type, SERVICE_CHOICE_DEFAULT)

    def test_get_user_credentials_by_ip_not_exists_lease(self):
        customer_service = Service.get_user_credentials_by_ip(
            ip_addr='10.11.12.12'
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_ip_if_ip_is_none(self):
        customer_service = Service.get_user_credentials_by_ip(
            ip_addr=None
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_ip_if_ip_is_bad(self):
        customer_service = Service.get_user_credentials_by_ip(
            ip_addr='10.11.12.12.13'
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_ip_customer_disabled(self):
        self.customer.is_active = False
        self.customer.save(update_fields=['is_active'])
        # self.customer.refresh_from_db()
        customer_service = Service.get_user_credentials_by_ip(
            ip_addr='10.11.12.2'
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_ip_customer_does_not_have_service(self):
        self.customer.stop_service(self.customer)
        customer_service = Service.get_user_credentials_by_ip(
            ip_addr='10.11.12.2'
        )
        self.assertIsNone(customer_service)


class GetUserCredentialsByDeviceOnuCredentialsTestCase(BaseServiceTestCase):
    def setUp(self):
        super().setUp()

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

    def test_get_user_credentials_by_device(self):
        customer_service = Service.get_user_credentials_by_device_onu(
            device_mac_addr=str(self.device_onu.mac_addr),
        )
        self.assertIsNotNone(customer_service)
        self.assertEqual(customer_service.speed_in, 10.0)
        self.assertEqual(customer_service.speed_out, 10.0)
        self.assertEqual(customer_service.speed_burst, 1)
        self.assertEqual(customer_service.cost, 10.0)
        self.assertEqual(customer_service.calc_type, SERVICE_CHOICE_DEFAULT)

    def test_get_user_credentials_by_device_not_exists(self):
        customer_service = Service.get_user_credentials_by_device_onu(
            device_mac_addr='1:2:3:4:5:6',
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_device_customer_disabled(self):
        self.customer_onu.is_active = False
        self.customer_onu.save(update_fields=['is_active'])
        # self.customer.refresh_from_db()
        customer_service = Service.get_user_credentials_by_device_onu(
            device_mac_addr=str(self.device_onu.mac_addr),
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_device_customer_does_not_have_service(self):
        self.customer_onu.stop_service(self.customer_onu)
        customer_service = Service.get_user_credentials_by_device_onu(
            device_mac_addr=str(self.device_onu.mac_addr),
        )
        self.assertIsNone(customer_service)
