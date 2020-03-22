from django.test import TestCase

from customers.tests import CustomAPITestCase
from devices.tests import DeviceTestCase
from services.models import Service, SERVICE_CHOICE_DEFAULT


class GetUserCredentialsByDeviceCredentialsTestCase(TestCase):
    def setUp(self):
        # Initialize customers instances
        CustomAPITestCase.setUp(self)

        # Initialize devices instances
        DeviceTestCase.setUp(self)

        self.customer.device = self.device_switch
        self.customer.dev_port = self.ports[1]
        self.customer.save()
        self.customer.refresh_from_db()

        self.service = Service.objects.create(
            title='test',
            descr='test',
            speed_in=10.0,
            speed_out=10.0,
            cost=10.0,
            calc_type=SERVICE_CHOICE_DEFAULT
        )

        self.customer.add_balance(self.admin, 10000, 'test')
        self.customer.save(update_fields=['balance'])
        self.customer.refresh_from_db()
        self.customer.pick_service(self.service, self.customer)

    def test_get_user_credentials_by_device_switch(self):
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
