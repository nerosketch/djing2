from decimal import Decimal
from typing import Optional
from datetime import datetime, timedelta
from django.db.models import F
from customers.models import CustomerLog, Customer
from customers.tests.customer import CustomAPITestCase
from networks.models import CustomerIpLeaseModel
from services.models import Service, CustomerService
from services.custom_logic import SERVICE_CHOICE_DEFAULT


class CustomerServiceAutoconnectTestCase(CustomAPITestCase):
    def setUp(self):
        super().setUp()

        # service for tests
        self.service = Service.objects.create(
            title="test service",
            speed_in=10.0,
            speed_out=10.0,
            cost=2,
            calc_type=0  # ServiceDefault
        )
        self.service.sites.add(self.site)

        self.customer.add_balance(
            profile=self.admin,
            cost=Decimal(10),
            comment='For tests'
        )
        self.customer.auto_renewal_service = True
        self.customer.save(update_fields=['balance', 'auto_renewal_service'])

        now = datetime.now()
        cs = self._pick_service(
            start_time=now,
            deadline=now + timedelta(seconds=3)
        )
        cs.refresh_from_db()
        self.cs = cs

    def _pick_service(self, deadline: datetime, service=None, start_time: Optional[datetime] = None):
        customer_service = CustomerService.objects.create(
            service=service or self.service,
            start_time=start_time or datetime.now(),
            deadline=deadline,
        )
        self.customer.current_service = customer_service
        self.customer.save(update_fields=['current_service'])
        self.customer.refresh_from_db()
        return customer_service

    def test_continue_service_ok(self):
        customer = self.customer

        # before all, initial
        self.assertEqual(customer.current_service.service.pk, self.service.pk)
        self.assertEqual(customer.balance, 10)
        CustomerService.objects.continue_services_if_autoconnect(customer=customer)

        # after first try, when time not expired
        self.assertEqual(customer.balance, 10)
        self.assertEqual(customer.current_service.service.pk, self.service.pk)

        # decrease time
        CustomerService.objects.filter(pk=self.cs.pk).update(
            start_time=F('start_time') - timedelta(minutes=1),
            deadline=F('deadline') - timedelta(minutes=1)
        )

        # now time is expired, continue service
        CustomerService.objects.continue_services_if_autoconnect(customer=customer)
        customer.refresh_from_db()
        self.assertEqual(customer.balance, 8)
        self.assertEqual(customer.current_service.service.pk, self.service.pk)

        logs = CustomerLog.objects.filter(
            customer=self.customer,
            from_balance=10,
            to_balance=8,
            cost=2,
        )
        self.assertTrue(logs.exists(), msg=logs)

    def test_get_user_credentials_by_ip(self):
        customer_service = CustomerService.get_user_credentials_by_ip(ip_addr="10.11.12.2")
        self.assertIsNotNone(customer_service)
        self.assertEqual(customer_service.service.speed_in, 10.0)
        self.assertEqual(customer_service.service.speed_out, 10.0)
        self.assertEqual(customer_service.service.speed_burst, 1)
        self.assertEqual(customer_service.service.cost, 10.0)
        self.assertEqual(customer_service.service.calc_type, SERVICE_CHOICE_DEFAULT)

    def test_not_exists_lease(self):
        customer_service = CustomerService.get_user_credentials_by_ip(ip_addr="10.11.12.12")
        self.assertIsNone(customer_service)

    def test_if_ip_is_none(self):
        customer_service = CustomerService.get_user_credentials_by_ip(ip_addr=None)
        self.assertIsNone(customer_service)

    def test_if_ip_is_bad(self):
        customer_service = CustomerService.get_user_credentials_by_ip(ip_addr="10.11.12.12.13")
        self.assertIsNone(customer_service)

    def test_customer_disabled(self):
        self.customer.is_active = False
        self.customer.save(update_fields=["is_active"])
        # self.customer.refresh_from_db()
        customer_service = CustomerService.get_user_credentials_by_ip(ip_addr="10.11.12.2")
        self.assertIsNone(customer_service)

    def test_customer_does_not_have_service(self):
        self.customer.stop_service(self.customer)
        customer_service = CustomerService.get_user_credentials_by_ip(ip_addr="10.11.12.2")
        self.assertIsNone(customer_service)

    def test_customer_with_onu_device(self):
        # customer for tests
        customer_onu = Customer.objects.create_user(
            telephone="+79782345679",
            username="custo_onu",
            password="passww",
            is_active=True
        )
        customer_onu.device = self.device_onu
        customer_onu.add_balance(self.admin, 10000, "test")
        customer_onu.save()
        customer_onu.refresh_from_db()
        customer_onu.pick_service(self.service, customer_onu)
        self.customer_onu = customer_onu

        self.lease = CustomerIpLeaseModel.objects.filter(
            ip_address="10.11.12.3",
        ).update(
            mac_address="1:2:3:4:5:6",
            pool=self.ippool,
            customer=customer_onu,
            is_dynamic=True,
        )
        self.assertIsNotNone(self.lease)
        # lease must be contain ip_address=10.11.12.3'

        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr="10.11.12.3",
        )
        self.assertIsNotNone(customer_service)
        self.assertEqual(customer_service.service.speed_in, 10.0)
        self.assertEqual(customer_service.service.speed_out, 10.0)
        self.assertEqual(customer_service.service.speed_burst, 1)
        self.assertEqual(customer_service.service.cost, 10.0)
        self.assertEqual(customer_service.service.calc_type, SERVICE_CHOICE_DEFAULT)
