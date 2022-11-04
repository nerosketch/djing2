from typing import Optional
from datetime import datetime, timedelta
from django.db.models import F
from customers.models import Customer, CustomerLog
from customers.tests.customer import CustomAPITestCase
from services.models import Service
from .models import CustomerService


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
            cost=10,
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
        Customer.objects.continue_services_if_autoconnect(customer=customer)

        # after first try, when time not expired
        self.assertEqual(customer.balance, 10)
        self.assertEqual(customer.current_service.service.pk, self.service.pk)

        # decrease time
        CustomerService.objects.filter(pk=self.cs.pk).update(
            start_time=F('start_time') - timedelta(minutes=1),
            deadline=F('deadline') - timedelta(minutes=1)
        )

        # now time is expired, continue service
        Customer.objects.continue_services_if_autoconnect(customer=customer)
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
