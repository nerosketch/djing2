from django.test import TestCase

from customers.models import Customer
from customers.tests import CustomAPITestCase
from devices.tests import DeviceTestCase
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


class GetUserCredentialsByDeviceSwitchCredentialsTestCase(BaseServiceTestCase):
    def setUp(self):
        super().setUp()

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save()
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

    def test_get_user_credentials_by_device(self):
        customer_service = Service.get_user_credentials_by_device_switch(
            device_mac_addr=str(self.device_switch.mac_addr),
            device_port=int(self.ports[1].num)
        )
        self.assertIsNotNone(customer_service)
        self.assertEqual(customer_service.speed_in, 10.0)
        self.assertEqual(customer_service.speed_out, 10.0)
        self.assertEqual(customer_service.speed_burst, 1)
        self.assertEqual(customer_service.cost, 10.0)
        self.assertEqual(customer_service.calc_type, SERVICE_CHOICE_DEFAULT)

    def test_get_user_credentials_by_device_not_exists_device(self):
        customer_service = Service.get_user_credentials_by_device_switch(
            device_mac_addr='1:2:3:4:5:6',
            device_port=int(self.ports[1].num)
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_device_not_exists_port(self):
        customer_service = Service.get_user_credentials_by_device_switch(
            device_mac_addr=str(self.device_switch.mac_addr),
            device_port=2345
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_device_customer_disabled(self):
        self.customer.is_active = False
        self.customer.save(update_fields=['is_active'])
        # self.customer.refresh_from_db()
        customer_service = Service.get_user_credentials_by_device_switch(
            device_mac_addr=str(self.device_switch.mac_addr),
            device_port=int(self.ports[1].num)
        )
        self.assertIsNone(customer_service)

    def test_get_user_credentials_by_device_customer_does_not_have_service(self):
        self.customer.stop_service(self.customer)
        customer_service = Service.get_user_credentials_by_device_switch(
            device_mac_addr=str(self.device_switch.mac_addr),
            device_port=int(self.ports[1].num)
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
