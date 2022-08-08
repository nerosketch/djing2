from hashlib import md5
from datetime import datetime, timedelta

from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.html import escape
from rest_framework.test import APITestCase
from rest_framework import status

from customers.models import Customer
from fin_app.models.alltime import AllTimePayGateway
from profiles.models import UserProfile
from fin_app.views.alltime import (
    AllTimePayActEnum,
    TRANSACTION_STATUS_PAYMENT_OK,
    AllTimeStatusCodeEnum
)
from fin_app.models import rncb as models_rncb
from fin_app.models import payme as models_payme


def _make_sign(act: AllTimePayActEnum, pay_account: str, serv_id: str, pay_id, secret: str):
    md = md5()
    s = "%d_%s_%s_%s_%s" % (act.value, pay_account, serv_id, pay_id, secret)
    md.update(bytes(s, "utf-8"))
    return md.hexdigest()


class CustomAPITestCase(APITestCase):
    def get(self, *args, **kwargs):
        return self.client.get(SERVER_NAME="example.com", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(SERVER_NAME="example.com", *args, **kwargs)

    def setUp(self):
        self.admin = UserProfile.objects.create_superuser(
            username="admin",
            password="admin",
            telephone="+797812345678",
            is_active=True
        )
        # customer for tests
        custo1 = Customer.objects.create_user(
            telephone="+79782345678",
            username="1234567",
            password="passw",
            is_active=True
        )
        custo1.balance = -13.12
        custo1.fio = "Test Name"
        custo1.save(update_fields=("balance", "fio"))
        custo1.refresh_from_db()
        self.customer = custo1

        # Pay System
        pay_system = AllTimePayGateway.objects.create(
            title="Test pay alltime system", secret="secret",
            service_id="service_id", slug="pay_gw_slug"
        )
        example_site = Site.objects.first()
        pay_system.sites.add(example_site)
        custo1.sites.add(example_site)
        pay_system.refresh_from_db()
        self.pay_system = pay_system


time_format = "%d.%m.%Y %H:%M"


class AllPayTestCase(CustomAPITestCase):
    url = "/api/fin/alltime/pay_gw_slug/pay/"

    def test_user_pay_view_info(self):
        current_date = timezone.now().strftime(time_format)
        service_id = self.pay_system.service_id
        r = self.get(self.url, {
            "ACT": AllTimePayActEnum.ACT_VIEW_INFO.value,
            "PAY_ACCOUNT": "1234567",
            "SIGN": _make_sign(
                AllTimePayActEnum.ACT_VIEW_INFO,
                "1234567", "", "", self.pay_system.secret
            )
        })
        o = "".join((
            "<pay-response>",
            "<balance>-13.12</balance>",
            "<name>Test Name</name>",
            "<account>1234567</account>",
            "<service_id>%s</service_id>" % escape(service_id),
            "<min_amount>10.0</min_amount>",
            "<max_amount>15000</max_amount>",
            "<status_code>%d</status_code>" % AllTimeStatusCodeEnum.PAYMENT_POSSIBLE.value,
            "<time_stamp>%s</time_stamp>" % escape(current_date),
            "</pay-response>",
        ))
        self.maxDiff = None
        self.assertXMLEqual(r.content.decode("utf8"), o)
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_user_pay_pay(self):
        current_date = timezone.now().strftime(time_format)
        service_id = self.pay_system.service_id
        r = self.get(self.url, {
            "ACT": AllTimePayActEnum.ACT_PAY_DO.value,
            "PAY_ACCOUNT": "1234567",
            "PAY_AMOUNT": 18.21,
            "RECEIPT_NUM": 2126235,
            "SERVICE_ID": service_id,
            "PAY_ID": "840ab457-e7d1-4494-8197-9570da035170",
            "TRADE_POINT": "term1",
            "SIGN": _make_sign(
                AllTimePayActEnum.ACT_PAY_DO,
                "1234567", service_id,
                "840ab457-e7d1-4494-8197-9570da035170",
                self.pay_system.secret
            )
        })
        xml = "".join((
            "<pay-response>",
            "<pay_id>840ab457-e7d1-4494-8197-9570da035170</pay_id>",
            "<service_id>%s</service_id>" % escape(service_id),
            "<amount>18.21</amount>",
            "<status_code>%d</status_code>" % AllTimeStatusCodeEnum.PAYMENT_OK.value,
            "<time_stamp>%s</time_stamp>" % escape(current_date),
            "</pay-response>",
        ))
        self.assertXMLEqual(r.content.decode("utf-8"), xml)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertEqual(round(self.customer.balance, 2), 5.09)
        self.user_pay_check(current_date)

    def user_pay_check(self, test_pay_time):
        current_date = timezone.now().strftime(time_format)
        service_id = self.pay_system.service_id
        r = self.get(self.url, {
            "ACT": AllTimePayActEnum.ACT_PAY_CHECK.value,
            "SERVICE_ID": service_id,
            "PAY_ID": "840ab457-e7d1-4494-8197-9570da035170",
            "SIGN": _make_sign(
                AllTimePayActEnum.ACT_PAY_CHECK,
                "", service_id,
                "840ab457-e7d1-4494-8197-9570da035170",
                self.pay_system.secret
            )
        })
        xml = "".join((
            "<pay-response>",
            "<status_code>%d</status_code>" % AllTimeStatusCodeEnum.TRANSACTION_STATUS_DETERMINED.value,
            "<time_stamp>%s</time_stamp>" % escape(current_date),
            "<transaction>",
            "<pay_id>840ab457-e7d1-4494-8197-9570da035170</pay_id>",
            "<service_id>%s</service_id>" % escape(service_id),
            "<amount>18.21</amount>",
            "<status>%d</status>" % TRANSACTION_STATUS_PAYMENT_OK,
            "<time_stamp>%s</time_stamp>" % escape(test_pay_time),
            "</transaction>",
            "</pay-response>",
        ))
        self.assertXMLEqual(r.content.decode(), xml)
        self.assertEqual(r.status_code, status.HTTP_200_OK)


class SitesAllPayTestCase(CustomAPITestCase):
    url = "/api/fin/alltime/pay_gw_slug/pay/"

    def setUp(self):
        super().setUp()
        another_site = Site.objects.create(domain="another.ru", name="another")
        pay_system = self.pay_system
        pay_system.sites.set([another_site])
        pay_system.refresh_from_db()

    def test_another_site(self):
        current_date = timezone.now().strftime(time_format)
        r = self.get(self.url, {
            "ACT": AllTimePayActEnum.ACT_VIEW_INFO.value,
            "PAY_ACCOUNT": "1234567",
            "SIGN": _make_sign(
                AllTimePayActEnum.ACT_VIEW_INFO,
                "1234567", "", "", self.pay_system.secret
            )
        })
        o = "".join((
            "<pay-response>",
            "<status_code>%d</status_code>" % AllTimeStatusCodeEnum.BAD_REQUEST.value,
            "<time_stamp>%s</time_stamp>" % escape(current_date),
            "<description>Pay gateway does not exist</description>",
            "</pay-response>",
        ))
        self.maxDiff = None
        self.assertXMLEqual(r.content.decode("utf8"), o)
        self.assertEqual(r.status_code, status.HTTP_200_OK)


class RNCBPaymentAPITestCase(APITestCase):
    url = "/api/fin/rncb/rncb_gw_slug/pay/"

    def get(self, *args, **kwargs):
        return self.client.get(SERVER_NAME="example.com", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(SERVER_NAME="example.com", *args, **kwargs)

    def setUp(self):
        self.admin = UserProfile.objects.create_superuser(
            username="admin",
            password="admin",
            telephone="+797812345678",
            is_active=True
        )
        # customer for tests
        custo1 = Customer.objects.create_user(
            telephone="+79782345678",
            username="129386",
            password="passw",
            is_active=True
        )
        custo1.balance = -13.12109349
        custo1.fio = "Test Name"
        custo1.save(update_fields=("balance", "fio"))
        custo1.refresh_from_db()
        self.customer = custo1

        # RNCB Pay system
        pay_system = models_rncb.RNCBPaymentGateway.objects.create(
            title="Test pay rncb system",
            slug="rncb_gw_slug"
        )
        example_site = Site.objects.first()
        pay_system.sites.add(example_site)
        custo1.sites.add(example_site)
        pay_system.refresh_from_db()
        self.pay_system = pay_system

    def test_pay_view(self):
        r = self.get(self.url, {
            "QueryType": 'check',
            "Account": "129386",
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<CHECKRESPONSE>"
            #  "<FIO>Test Name</FIO>"
            "<BALANCE>-13.12</BALANCE>"
            "<ERROR>0</ERROR>"
            "<COMMENTS>Ok</COMMENTS>"
            "</CHECKRESPONSE>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertXMLEqual(r.content.decode("utf-8"), xml)

    def test_pay_view_unknown_account(self):
        r = self.get(self.url, {
            "QueryType": 'check',
            "Account": "12089",
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<CHECKRESPONSE>"
            "<ERROR>1</ERROR>"
            "<COMMENTS>Customer does not exists</COMMENTS>"
            "</CHECKRESPONSE>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertXMLEqual(r.content.decode("utf-8"), xml, r.data)

    def test_pay_view_bad_account(self):
        r = self.get(self.url, {
            "QueryType": 'check',
            "Account": "*7867^&a",
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<CHECKRESPONSE>"
            "<ERROR>1</ERROR>"
            "<COMMENTS>Account: Введите правильное число.</COMMENTS>"
            "</CHECKRESPONSE>"
        )
        self.assertXMLEqual(r.content.decode("utf-8"), xml, r.data)

    def test_pay(self):
        r = self.get(self.url, {
            "QueryType": 'pay',
            "Account": "129386",
            "Payment_id": 12983,
            "Summa": 198.123321,
            "Exec_date": "20170101182810",
            "Inn": 1234567891
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<PAYRESPONSE>"
            "<OUT_PAYMENT_ID>2</OUT_PAYMENT_ID>"
            "<ERROR>0</ERROR>"
            "<COMMENTS>Success</COMMENTS>"
            "</PAYRESPONSE>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertXMLEqual(r.content.decode("utf-8"), xml)

    def test_pay_already_provided(self):
        now = datetime.now()
        pay = models_rncb.RNCBPaymentLog.objects.create(
            customer=self.customer,
            pay_id=1927863123,
            acct_time=now,
            amount=12.344,
            pay_gw=self.pay_system
        )
        r = self.get(self.url, {
            "QueryType": 'pay',
            "Account": "129386",
            "Payment_id": 1927863123,
            "Summa": 198.123321,
            "Exec_date": "20170101182810",
            "Inn": 1234567891
        })
        xml = ''.join((
            '<?xml version="1.0" encoding="utf-8"?>\n',
            "<PAYRESPONSE>",
            "<OUT_PAYMENT_ID>%d</OUT_PAYMENT_ID>" % pay.pk,
            "<ERROR>10</ERROR>",
            "<COMMENTS>Payment duplicate</COMMENTS>",
            "</PAYRESPONSE>"
        ))
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertXMLEqual(r.content.decode("utf-8"), xml)


class RNCBPaymentBalanceCheckerAPITestCase(APITestCase):
    url = "/api/fin/rncb/rncb_gw_slug/pay/"

    def get(self, *args, **kwargs):
        return self.client.get(SERVER_NAME="example.com", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client.post(SERVER_NAME="example.com", *args, **kwargs)

    def setUp(self):
        # customer for tests
        custo1 = Customer.objects.create_user(
            telephone="+79782345678",
            username="129386",
            password="passw",
            is_active=True
        )
        custo1.balance = -13.12
        custo1.fio = "Test Name"
        custo1.save(update_fields=("balance", "fio"))
        custo1.refresh_from_db()
        self.customer = custo1

        # RNCB Pay system
        pay_system = models_rncb.RNCBPaymentGateway.objects.create(
            title="Test pay rncb system",
            slug="rncb_gw_slug"
        )
        example_site = Site.objects.first()
        pay_system.sites.add(example_site)
        custo1.sites.add(example_site)
        pay_system.refresh_from_db()
        self.pay_system = pay_system

        now = datetime(year=2017, month=1, day=1)

        logs = [
            models_rncb.RNCBPaymentLog(
                customer=self.customer,
                pay_id=12837,
                acct_time=now,
                amount=1,
                pay_gw=self.pay_system
            ),
            models_rncb.RNCBPaymentLog(
                customer=self.customer,
                pay_id=12838,
                acct_time=now + timedelta(days=2),
                amount=2,
                pay_gw=self.pay_system
            ),
            models_rncb.RNCBPaymentLog(
                customer=self.customer,
                pay_id=12839,
                acct_time=now + timedelta(days=6),
                amount=3,
                pay_gw=self.pay_system
            ),
            models_rncb.RNCBPaymentLog(
                customer=self.customer,
                pay_id=12840,
                acct_time=now + timedelta(days=8),
                amount=5,
                pay_gw=self.pay_system
            )
        ]
        for log in logs:
            log.save()

    def test_pay_balance_check(self):
        r = self.get(self.url, {
            "QueryType": 'balance',
            "DateFrom": '20170101000000',
            "DateTo": '2017012200000',
            #  "Inn": 1234567891
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<BALANCERESPONSE>"
              "<FULL_SUMMA>11.00</FULL_SUMMA>"
              "<NUMBER_OF_PAYMENTS>4</NUMBER_OF_PAYMENTS>"
              "<ERROR>0</ERROR>"
              "<PAYMENTS>"
                "<PAYMENT_ROW>12837;4;129386;1.00;20170101000000</PAYMENT_ROW>"
                "<PAYMENT_ROW>12838;5;129386;2.00;20170103000000</PAYMENT_ROW>"
                "<PAYMENT_ROW>12839;6;129386;3.00;20170107000000</PAYMENT_ROW>"
                "<PAYMENT_ROW>12840;7;129386;5.00;20170109000000</PAYMENT_ROW>"
              "</PAYMENTS>"
            "</BALANCERESPONSE>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.maxDiff = None
        self.assertXMLEqual(r.content.decode("utf-8"), xml)


class PaymeMerchantApiTestCase(CustomAPITestCase):
    url = '/api/fin/payme/pay_gw_slug/pay/'

    def setUp(self):
        super().setUp()
        # Pay System
        pay_system = models_payme.PaymePaymentGatewayModel.objects.create(
            title="Test pay payme system",
            slug="pay_gw_slug"
        )
        example_site = Site.objects.first()
        pay_system.sites.add(example_site)
        pay_system.refresh_from_db()
        self.payme_pay_system = pay_system

    def test_check_perform_transaction(self):
        r = self.post(self.url, data={
            "method" : "CheckPerformTransaction",
            "params" : {
                "amount" : 5000,
                "account" : {
                    "username" : "1234567"
                }
            },
            'id': 19283
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertDictEqual(r.data, {
            "result" : {
                "allow" : True
            }
        }, msg=r.data)

    def test_check_perform_transaction_no_account(self):
        r = self.post(self.url, data={
            "method" : "CheckPerformTransaction",
            "params" : {
                "amount" : 5000,
                "account" : {
                    "username" : "12222222"
                }
            },
            'id': 19283
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertDictEqual(r.data, {
            "error" : {
                "code" : -31050,
                "message": {
                    'ru': 'Абонент не найден',
                    'en': 'Customer does not exists'
                },
                "data": 'username'
            },
            'id': 19283
        }, msg=r.data)

    def test_check_perform_transaction_disabled_customer(self):
        self.customer.is_active = False
        self.customer.save(update_fields=['is_active'])
        r = self.post(self.url, data={
            "method" : "CheckPerformTransaction",
            "params" : {
                "amount" : 5000,
                "account" : {
                    "username" : "1234567"
                }
            },
            'id': 19283
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertDictEqual(r.data, {
            "error" : {
                "code" : -31050,
                "message": {
                    'ru': 'Абонент не найден',
                    'en': 'Customer does not exists'
                },
                "data": 'username'
            },
            'id': 19283
        }, msg=r.data)

    def test_check_perform_transaction_bad_request(self):
        r = self.post(self.url, data={
            "method" : "CheckPerformTransaction",
            "params" : {
                "amjount" : 'aosid',
                "account" : {
                    "nbv" : "1234567"
                }
            },
            'id': 19283
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertDictEqual(r.data, {
            'error': {
                'code': -32700,
                'message': {
                    'ru': 'Ошибка валидации данных',
                    'en': 'Data validation error'
                },
                'data': 'username'
            }
        }, msg=r.data)

    def test_check_perform_transaction_no_post(self):
        def _assert_no_post(dct):
            self.assertDictEqual(dct, {
                'error': {
                    'code': -32300,
                    'message': {
                        'ru': 'HTTP Метод не допустим',
                        'en': 'HTTP Method is not allowed'
                    },
                    'data': 'username'
                }
            })

        r = self.client.get(self.url, SERVER_NAME="example.com")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        _assert_no_post(r.data)

        r = self.client.put(self.url, {}, SERVER_NAME="example.com")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        _assert_no_post(r.data)

        r = self.client.delete(self.url, {}, SERVER_NAME="example.com")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        _assert_no_post(r.data)

        r = self.client.head(self.url, {}, SERVER_NAME="example.com")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        _assert_no_post(r.data)

        r = self.client.options(self.url, {}, SERVER_NAME="example.com")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        _assert_no_post(r.data)

        r = self.client.trace(self.url, {}, SERVER_NAME="example.com")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        _assert_no_post(r.data)

        r = self.client.patch(self.url, {}, SERVER_NAME="example.com")
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        _assert_no_post(r.data)

    def test_create_transaction(self):
        now = datetime.now()
        r = self.post(self.url, {
            "method": "CreateTransaction",
            "params": {
                "id": "5305e3bab097f420a62ced0b",
                "time" : 1399114284039,
                "amount" : 500000,
                "account" : {
                    "username" : "1234567"
                }
            }
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        res = r.data.get('result')
        self.assertIsNotNone(res, msg=r.data)
        self.assertIsInstance(res['transaction'], int)
        self.assertTrue(res['transaction'] > 0)
        self.assertEqual(res['state'], 1)
        # Compare create time with accuracy to seconds
        self.assertEqual(int(res['create_time'] / 1000), int(now.timestamp()))

    def test_create_transaction_duplicate(self):
        self.test_create_transaction()
        self.test_create_transaction()
        self.test_create_transaction()
        self.test_create_transaction()

    def test_perform_transaction(self):
        # create transaction
        self.test_create_transaction()
        # perform transaction
        r = self.post(self.url, {
            "method": "PerformTransaction",
            "params": {
                "id": "5305e3bab097f420a62ced0b",
            }
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        res = r.data.get('result')
        self.assertIsNotNone(res, msg=r.data)
        self.assertIsInstance(res['transaction'], int)
        self.assertTrue(res['transaction'] > 0)
        self.assertIsInstance(res['perform_time'], int)
        self.assertTrue(res['perform_time'] > 0)
        self.assertEqual(res['state'], 2)
