from typing import Optional
from datetime import datetime, timedelta

from django.utils.translation import gettext as _
from rest_framework.settings import api_settings
from starlette import status

from customers.models import Customer
from customers.tests.customer import CustomAPITestCase
from services.models import Service


class PickServiceAPITestCase(CustomAPITestCase):
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

    def _pick_service_request(self, deadline: Optional[datetime] = None):
        if deadline is None:
            deadline = datetime.now() + timedelta(days=5)
        dtime_fmt = getattr(api_settings, "DATETIME_FORMAT", "%Y-%m-%d %H:%M")
        r = self.post(
            "/api/customer_service/%d/pick_service/" % self.customer.pk,
            {
                "service_id": self.service.pk,
                "deadline": deadline.strftime(dtime_fmt)
            },
            )
        return r

    def test_pick_service_not_enough_money(self):
        Customer.objects.filter(username="custo1").update(balance=0)
        r = self._pick_service_request()
        self.assertEqual(r.text, 'Ok')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, -2)
        self.assertEqual(self.customer.current_service.service, self.service)

    def test_pick_service(self):
        Customer.objects.filter(username="custo1").update(balance=2)
        self.customer.refresh_from_db()
        r = self._pick_service_request()
        self.assertEqual(r.text, 'Ok')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_pick_service_again(self):
        self.test_pick_service()
        self.customer.refresh_from_db()
        r = self._pick_service_request()
        self.assertEqual(r.json()['detail'], _('That service already activated'))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pick_service_with_now_deadline(self):
        Customer.objects.filter(username="custo1").update(balance=2)
        self.customer.refresh_from_db()
        r = self._pick_service_request(
            deadline=datetime.now()
        )
        self.assertEqual(r.json(), _("Deadline can't be in past"))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.text)

    def test_pick_service_with_past_deadline(self):
        Customer.objects.filter(username="custo1").update(balance=2)
        self.customer.refresh_from_db()
        r = self._pick_service_request(
            deadline=datetime.now() - timedelta(minutes=2)
        )
        self.assertEqual(r.json(), _("Deadline can't be in past"))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stop_service(self):
        self.test_pick_service()
        r = self.get("/api/customers/%d/stop_service/" % self.customer.pk)
        self.assertFalse(r.text, msg=r.text)
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_pick_admin_service_by_customer(self):
        self.logout()
        self.login(username='custo1')

        r = self._pick_service_request()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN, msg=r.content)
