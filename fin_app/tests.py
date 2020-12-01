from hashlib import md5

# from django.test.utils import override_settings
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.html import escape
from rest_framework.test import APITestCase

from customers.models import Customer
from fin_app.models import PayAllTimeGateway
from profiles.models import UserProfile


def _make_sign(act: int, pay_account: str, serv_id: str, pay_id, secret: str):
    md = md5()
    s = "%d_%s_%s_%s_%s" % (act, pay_account, serv_id, pay_id, secret)
    md.update(bytes(s, 'utf-8'))
    return md.hexdigest()


# @override_settings(DEFAULT_TABLESPACE='ram')
class CustomAPITestCase(APITestCase):
    def get(self, *args, **kwargs):
        return self.client.get(SERVER_NAME='example.com', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(SERVER_NAME='example.com', *args, **kwargs)

    def setUp(self):
        self.admin = UserProfile.objects.create_superuser(
            username='admin',
            password='admin',
            telephone='+797812345678'
        )
        # customer for tests
        custo1 = Customer.objects.create_user(
            telephone='+79782345678',
            username='custo1',
            password='passw'
        )
        custo1.balance = -13.12
        custo1.fio = 'Test Name'
        custo1.save(update_fields=('balance', 'fio'))
        custo1.refresh_from_db()
        self.customer = custo1

        # Pay System
        pay_system = PayAllTimeGateway.objects.create(
            title='Test pay system',
            secret='secret',
            service_id='service_id',
            slug='pay_gw_slug'
        )
        example_site = Site.objects.first()
        pay_system.sites.add(example_site)
        pay_system.refresh_from_db()
        self.pay_system = pay_system


class AllPayTestCase(CustomAPITestCase):
    time_format = '%d.%m.%Y %H:%M'
    url = '/api/fin/pay_gw_slug/pay/'

    def test_user_pay_view_info(self):
        current_date = timezone.now().strftime(self.time_format)
        service_id = self.pay_system.service_id
        r = self.get(self.url, {
                'ACT': 1,
                'PAY_ACCOUNT': 'custo1',
                'SIGN': _make_sign(1, 'custo1', '', '', self.pay_system.secret)
            })
        o = ''.join((
            "<pay-response>",
                "<balance>-13.12</balance>",
                "<name>Test Name</name>",
                "<account>custo1</account>",
                "<service_id>%s</service_id>" % escape(service_id),
                "<min_amount>10.0</min_amount>",
                "<max_amount>15000</max_amount>",
                "<status_code>21</status_code>",
                "<time_stamp>%s</time_stamp>" % escape(current_date),
            "</pay-response>"
        ))
        self.maxDiff = None
        self.assertXMLEqual(r.content.decode('utf8'), o)
        self.assertEqual(r.status_code, 200)

    def test_user_pay_pay(self):
        current_date = timezone.now().strftime(self.time_format)
        service_id = self.pay_system.service_id
        r = self.get(self.url, {
            'ACT': 4,
            'PAY_ACCOUNT': 'custo1',
            'PAY_AMOUNT': 18.21,
            'RECEIPT_NUM': 2126235,
            'SERVICE_ID': service_id,
            'PAY_ID': '840ab457-e7d1-4494-8197-9570da035170',
            'TRADE_POINT': 'term1',
            'SIGN': _make_sign(4, 'custo1', service_id,
                               '840ab457-e7d1-4494-8197-9570da035170', self.pay_system.secret)
        })
        xml = ''.join((
            "<pay-response>",
                "<pay_id>840ab457-e7d1-4494-8197-9570da035170</pay_id>",
                "<service_id>%s</service_id>" % escape(service_id),
                "<amount>18.21</amount>",
                "<status_code>22</status_code>",
                "<time_stamp>%s</time_stamp>" % escape(current_date),
            "</pay-response>"
        ))
        self.assertXMLEqual(r.content.decode('utf-8'), xml)
        self.assertEqual(r.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(round(self.customer.balance, 2), 5.09)
        self.user_pay_check(current_date)

    def user_pay_check(self, test_pay_time):
        current_date = timezone.now().strftime(self.time_format)
        service_id = self.pay_system.service_id
        r = self.get(self.url, {
            'ACT': 7,
            'SERVICE_ID': service_id,
            'PAY_ID': '840ab457-e7d1-4494-8197-9570da035170',
            'SIGN': _make_sign(7, '', service_id,
                               '840ab457-e7d1-4494-8197-9570da035170', self.pay_system.secret)
        })
        xml = ''.join((
            "<pay-response>",
                "<status_code>11</status_code>",
                "<time_stamp>%s</time_stamp>" % escape(current_date),
                "<transaction>",
                "<pay_id>840ab457-e7d1-4494-8197-9570da035170</pay_id>",
                "<service_id>%s</service_id>" % escape(service_id),
                "<amount>18.21</amount>",
                "<status>111</status>",
                "<time_stamp>%s</time_stamp>" % escape(test_pay_time),
                "</transaction>"
            "</pay-response>"
        ))
        self.assertXMLEqual(r.content.decode(), xml)
        self.assertEqual(r.status_code, 200)


class SitesAllPayTestCase(CustomAPITestCase):
    url = '/api/fin/pay_gw_slug/pay/'

    def setUp(self):
        super().setUp()
        another_site = Site.objects.create(
            domain='another.ru',
            name='another'
        )
        pay_system = self.pay_system
        pay_system.sites.set([another_site])
        pay_system.refresh_from_db()

    def test_another_site(self):
        r = self.get(self.url, {
            'ACT': 1,
            'PAY_ACCOUNT': 'custo1',
            'SIGN': _make_sign(1, 'custo1', '', '', self.pay_system.secret)
        })
        o = ''.join((
            "<pay-response>",
                "<detail>Не найдено.</detail>",
            "</pay-response>"
        ))
        self.maxDiff = None
        self.assertXMLEqual(r.content.decode('utf8'), o)
        self.assertEqual(r.status_code, 404)
