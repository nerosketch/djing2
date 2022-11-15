from datetime import datetime, timedelta

from django.contrib.sites.models import Site
from django.utils.translation import gettext as _
from rest_framework.settings import api_settings
from rest_framework import status
from customers import models
from groupapp.models import Group
from services.models import Service
from djing2.lib.fastapi.test import DjingTestCase
from rest_framework.authtoken.models import Token


class CustomAPITestCase(DjingTestCase):
    def setUp(self):
        super().setUp()

        self.group = Group.objects.create(title="test group", code="tst")

        # customer for tests
        custo1 = models.Customer.objects.create_user(
            telephone="+79782345678", username="custo1", password="passw",
            is_dynamic_ip=True, group=self.group,
            is_active=True
        )
        Token.objects.create(user=custo1)
        example_site = Site.objects.first()
        custo1.sites.add(example_site)
        custo1.refresh_from_db()
        self.customer = custo1
        self.site = example_site


class CustomerModelAPITestCase(CustomAPITestCase):
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

    def _pick_service_request(self):
        dtime_fmt = getattr(api_settings, "DATETIME_FORMAT", "%Y-%m-%d %H:%M")
        r = self.post(
            "/api/customers/%d/pick_service/" % self.customer.pk,
            {"service_id": self.service.pk, "deadline": (datetime.now() + timedelta(days=5)).strftime(dtime_fmt)},
            )
        return r

    def test_get_random_username(self):
        r = self.get("/api/customers/generate_username/")
        random_unique_uname = r.content
        qs = models.Customer.objects.filter(username=random_unique_uname)
        self.assertFalse(qs.exists())

    def test_pick_service_not_enough_money(self):
        models.Customer.objects.filter(username="custo1").update(balance=0)
        r = self._pick_service_request()
        self.assertEqual(r.text, 'Ok')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, -2)
        self.assertEqual(self.customer.current_service.service, self.service)

    def test_pick_service(self):
        models.Customer.objects.filter(username="custo1").update(balance=2)
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

    def test_stop_service(self):
        self.test_pick_service()
        r = self.get("/api/customers/%d/stop_service/" % self.customer.pk)
        self.assertFalse(r.text, msg=r.text)
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_stop_not_exists_service(self):
        models.Customer.objects.filter(username="custo1").update(current_service=None)
        r = self.get("/api/customers/%d/stop_service/" % self.customer.pk)
        self.assertEqual(r.text, _("Service not connected"))
        self.assertEqual(r.status_code, status.HTTP_418_IM_A_TEAPOT)

    def test_pick_admin_service_by_customer(self):
        self.logout()
        self.login(username='custo1')

        r = self._pick_service_request()
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN, msg=r.content)

    def test_pick_service_by_customer_low_money(self):
        self.logout()
        self.login(username='custo1')

        models.Customer.objects.filter(username="custo1").update(balance=0)
        self.customer.refresh_from_db()
        r = self.post("/api/customers/users/me/buy_service/", {"service_id": self.service.pk})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.json()['detail'], _("%(uname)s not enough money for service %(srv_name)s") % {
            'uname': self.customer.username,
            'srv_name': self.service
        })

    def test_pick_service_by_customer(self):
        self.logout()
        self.login(username='custo1')

        models.Customer.objects.filter(username="custo1").update(balance=2)
        self.customer.refresh_from_db()
        r = self.post("/api/customers/users/me/buy_service/", {"service_id": self.service.pk})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json(), "The service '%s' was successfully activated" % self.service)

    def test_add_balance_negative(self):
        r = self.post("/api/customers/%d/add_balance/" % self.customer.pk, {"cost": -10})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_add_balance_zero(self):
        r = self.post("/api/customers/%d/add_balance/" % self.customer.pk, {"cost": 0})
        self.assertEqual(r.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_add_balance_text_invalid(self):
        r = self.post("/api/customers/%d/add_balance/" % self.customer.pk, {"cost": "sadasd"})
        self.assertEqual(r.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_add_balance_ok(self):
        r = self.post("/api/customers/%d/add_balance/" % self.customer.pk, {"cost": 523})
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_add_balance_big(self):
        r = self.c.post(
            url="/api/customers/%d/add_balance/" % self.customer.pk,
            data=b'{"cost": %d}' % 0xff ** 0xff
        )
        self.assertEqual(r.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, msg=r.text)

    def test_add_balance_long_comment(self):
        r = self.post("/api/customers/%d/add_balance/" % self.customer.pk, {"cost": 0xFF, "comment": "text " * 0xFFF})
        self.assertEqual(r.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_add_balance_comment_bin(self):
        r = self.c.post(
            "/api/customers/%d/add_balance/" % self.customer.pk,
            data=b'{"cost": %d, "comment": %b}' % (
                0xFF,
                bytes("".join(chr(i) for i in range(10)), encoding="utf8")
            )
        )
        self.assertEqual(r.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, msg=r.json())


class InvoiceForPaymentAPITestCase(CustomAPITestCase):
    def setUp(self):
        super().setUp()

        self.inv1 = models.InvoiceForPayment.objects.create(
            customer=self.customer, status=False, cost=12, comment="Test invoice", author=self.admin
        )
        self.inv2 = models.InvoiceForPayment.objects.create(
            customer=self.customer, status=False, cost=14, comment="Test invoice2", author=self.admin
        )

    def test_buy_empty_data(self):
        self.logout()
        self.login(username='custo1')

        r = self.post("/api/customers/users/debts/%d/buy/" % self.inv1.pk, data={'sure': 'asd'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, msg=r.text)
        self.assertDictEqual(r.json(), {'detail': _("Are you not sure that you want buy the service?")})

    def test_buy_not_enough_money(self):
        self.logout()
        self.login(username='custo1')

        r = self.post("/api/customers/users/debts/%d/buy/" % self.inv1.pk, {"sure": "on"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.json()['detail'], _("Your account have not enough money"))

    def test_buy(self):
        self.logout()
        self.login(username='custo1')

        models.Customer.objects.filter(username="custo1").update(balance=12)
        self.customer.refresh_from_db()
        r = self.post("/api/customers/users/debts/%d/buy/" % self.inv1.pk, {"sure": "on"})
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(r.text, '')
        self.inv1.refresh_from_db()
        self.assertTrue(self.inv1.status)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, 0)

    def test_buy_not_auth(self):
        self.logout()
        r = self.post("/api/customers/users/debts/%d/buy/" % self.inv1.pk, {"sure": "on"})
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class UserTaskAPITestCase(CustomAPITestCase):
    def test_task_list(self):
        self.logout()
        self.login(username='custo1')
        r = self.get("/api/tasks/users/task_history/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_task_list_from_admin_user(self):
        self.logout()
        self.login(username='custo1')
        r = self.get("/api/tasks/users/task_history/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_task_link_unauth(self):
        self.logout()
        r = self.get("/api/tasks/users/task_history/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
