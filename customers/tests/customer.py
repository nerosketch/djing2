from datetime import datetime, timedelta

from django.test import override_settings
from django.utils.translation import gettext as _
from rest_framework.test import APITestCase
from rest_framework import status
from customers import models
from groupapp.tests import BaseGroupTestCase
from services.models import Service
from profiles.models import UserProfile


@override_settings(DEFAULT_TABLESPACE='ram')
class CustomAPITestCase(APITestCase):
    def get(self, *args, **kwargs):
        return self.client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(*args, **kwargs)

    def setUp(self):
        BaseGroupTestCase.setUp(self)

        self.admin = UserProfile.objects.create_superuser(
            username='admin',
            password='admin',
            telephone='+797812345678'
        )
        self.client.login(
            username='admin',
            password='admin'
        )
        # customer for tests
        custo1 = models.Customer.objects.create_user(
            telephone='+79782345678',
            username='custo1',
            password='passw',
            group=self.group
        )
        custo1.refresh_from_db()
        self.customer = custo1


class CustomerServiceTestCase(CustomAPITestCase):
    def test_direct_create(self):
        r = self.post('/api/customers/customer-service/')
        self.assertEqual(r.data, _("Not allowed to direct create Customer service, use 'pick_service' url"))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class CustomerLogAPITestCase(CustomAPITestCase):
    def test_direct_create(self):
        r = self.post('/api/customers/customer-log/')
        self.assertEqual(r.data, _("Not allowed to direct create Customer log"))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class CustomerModelAPITestCase(CustomAPITestCase):
    def setUp(self):
        super().setUp()

        # service for tests
        self.service = Service.objects.create(
            title='test service',
            speed_in=10.0,
            speed_out=10.0,
            cost=2,
            calc_type=0  # ServiceDefault
        )

    def test_get_random_username(self):
        r = self.get('/api/customers/generate_username/')
        random_unique_uname = r.data
        qs = models.Customer.objects.filter(username=random_unique_uname)
        self.assertFalse(qs.exists())

    def test_pick_service_not_enough_money(self):
        models.Customer.objects.filter(username='custo1').update(balance=0)
        r = self.post('/api/customers/%d/pick_service/' % self.customer.pk, {
            'service_id': self.service.pk,
            'deadline': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')
        })
        self.customer.refresh_from_db()
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data)
        self.assertEqual(self.customer.balance, -2)
        self.assertEqual(self.customer.current_service.service, self.service)

    def test_pick_service(self):
        models.Customer.objects.filter(username='custo1').update(balance=2)
        self.customer.refresh_from_db()
        r = self.post('/api/customers/%d/pick_service/' % self.customer.pk, {
            'service_id': self.service.pk,
            'deadline': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')
        })
        self.assertIsNone(r.data)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_pick_service_again(self):
        self.test_pick_service()
        self.customer.refresh_from_db()
        r = self.post('/api/customers/%d/pick_service/' % self.customer.pk, {
            'service_id': self.service.pk,
            'deadline': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')
        })
        self.assertEqual(r.data, _('That service already activated'))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stop_service(self):
        self.test_pick_service()
        r = self.get('/api/customers/%d/stop_service/' % self.customer.pk)
        self.assertIsNone(r.data)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_stop_not_exists_service(self):
        models.Customer.objects.filter(username='custo1').update(current_service=None)
        r = self.get('/api/customers/%d/stop_service/' % self.customer.pk)
        self.assertEqual(r.data, _('Service not connected'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_pick_admin_service_by_customer(self):
        self.client.logout()
        login_r = self.client.login(
            username='custo1',
            password='passw'
        )
        self.assertTrue(login_r)
        r = self.post('/api/customers/%d/pick_service/' % self.customer.pk, {
            'service_id': self.service.pk,
            'deadline': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')
        })
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_pick_service_by_customer_low_money(self):
        self.client.logout()
        login_r = self.client.login(
            username='custo1',
            password='passw'
        )
        self.assertTrue(login_r)
        models.Customer.objects.filter(username='custo1').update(balance=0)
        self.customer.refresh_from_db()
        r = self.post('/api/customers/users/me/buy_service/', {
            'service_id': self.service.pk
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data, _('%(uname)s not enough money for service %(srv_name)s') % {
            'uname': self.customer.username,
            'srv_name': self.service
        })

    def test_pick_service_by_customer(self):
        self.client.logout()
        login_r = self.client.login(
            username='custo1',
            password='passw'
        )
        self.assertTrue(login_r)
        models.Customer.objects.filter(username='custo1').update(balance=2)
        self.customer.refresh_from_db()
        r = self.post('/api/customers/users/me/buy_service/', {
            'service_id': self.service.pk
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data, _("The service '%s' was successfully activated") % self.service)

    def test_add_balance_negative(self):
        r = self.post('/api/customers/%d/add_balance/' % self.customer.pk, {
            'cost': -10
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_add_balance_zero(self):
        r = self.post('/api/customers/%d/add_balance/' % self.customer.pk, {
            'cost': 0
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_balance_text_invalid(self):
        r = self.post('/api/customers/%d/add_balance/' % self.customer.pk, {
            'cost': 'sadasd'
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_balance_ok(self):
        r = self.post('/api/customers/%d/add_balance/' % self.customer.pk, {
            'cost': 523
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_add_balance_big(self):
        r = self.post('/api/customers/%d/add_balance/' % self.customer.pk, {
            'cost': 0xff ** 0xff
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_balance_long_comment(self):
        r = self.post('/api/customers/%d/add_balance/' % self.customer.pk, {
            'cost': 0xff,
            'comment': 'text ' * 0xfff
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_balance_comment_bin(self):
        r = self.post('/api/customers/%d/add_balance/' % self.customer.pk, {
            'cost': 0xff,
            'comment': bytes(''.join(chr(i) for i in range(10)), encoding='utf8')
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)


class InvoiceForPaymentAPITestCase(CustomAPITestCase):
    def setUp(self):
        super().setUp()

        self.inv1 = models.InvoiceForPayment.objects.create(
            customer=self.customer,
            status=False,
            cost=12,
            comment='Test invoice',
            author=self.admin
        )
        self.inv2 = models.InvoiceForPayment.objects.create(
            customer=self.customer,
            status=False,
            cost=14,
            comment='Test invoice2',
            author=self.admin
        )

    def test_buy_empty_data(self):
        self.client.logout()
        login_r = self.client.login(
            username='custo1',
            password='passw'
        )
        self.assertTrue(login_r)
        r = self.post('/api/customers/users/debts/%d/buy/' % self.inv1.pk)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data, _('Are you not sure that you want buy the service?'))

    def test_buy_not_enough_money(self):
        self.client.logout()
        login_r = self.client.login(
            username='custo1',
            password='passw'
        )
        self.assertTrue(login_r)
        r = self.post('/api/customers/users/debts/%d/buy/' % self.inv1.pk, {
            'sure': 'on'
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r.data, _('Your account have not enough money'))

    def test_buy(self):
        self.client.logout()
        login_r = self.client.login(
            username='custo1',
            password='passw'
        )
        self.assertTrue(login_r)
        models.Customer.objects.filter(username='custo1').update(balance=12)
        self.customer.refresh_from_db()
        r = self.post('/api/customers/users/debts/%d/buy/' % self.inv1.pk, {
            'sure': 'on'
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data)
        self.inv1.refresh_from_db()
        self.assertTrue(self.inv1.status)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.balance, 0)

    def test_buy_not_auth(self):
        self.client.logout()
        r = self.post('/api/customers/users/debts/%d/buy/' % self.inv1.pk, {
            'sure': 'on'
        })
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


class UserTaskAPITestCase(CustomAPITestCase):
    def test_task_list(self):
        self.client.logout()
        self.client.login(
            username='custo1',
            password='passw'
        )
        r = self.get('/api/tasks/users/task_history/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_task_list_from_admin_user(self):
        self.client.logout()
        self.client.login(
            username='admin',
            password='admin'
        )
        r = self.get('/api/tasks/users/task_history/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_task_link_unauth(self):
        self.client.logout()
        r = self.get('/api/tasks/users/task_history/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
