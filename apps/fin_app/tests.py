from hashlib import md5
from datetime import datetime, timedelta

from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.html import escape
from rest_framework.test import APITestCase
from rest_framework import status

from customers.models import Customer
from fin_app.models.alltime import PayAllTimeGateway
from profiles.models import UserProfile
from fin_app.views.alltime import (
    AllTimePayActEnum,
    TRANSACTION_STATUS_PAYMENT_OK,
    AllTimeStatusCodeEnum
)
from fin_app.models import rncb as models_rncb


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
            telephone="+797812345678"
        )
        # customer for tests
        custo1 = Customer.objects.create_user(
            telephone="+79782345678",
            username="custo1",
            password="passw"
        )
        custo1.balance = -13.12
        custo1.fio = "Test Name"
        custo1.save(update_fields=("balance", "fio"))
        custo1.refresh_from_db()
        self.customer = custo1

        # Pay System
        pay_system = PayAllTimeGateway.objects.create(
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
            "PAY_ACCOUNT": "custo1",
            "SIGN": _make_sign(
                AllTimePayActEnum.ACT_VIEW_INFO,
                "custo1", "", "", self.pay_system.secret
            )
        })
        o = "".join((
            "<pay-response>",
            "<balance>-13.12</balance>",
            "<name>Test Name</name>",
            "<account>custo1</account>",
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
            "PAY_ACCOUNT": "custo1",
            "PAY_AMOUNT": 18.21,
            "RECEIPT_NUM": 2126235,
            "SERVICE_ID": service_id,
            "PAY_ID": "840ab457-e7d1-4494-8197-9570da035170",
            "TRADE_POINT": "term1",
            "SIGN": _make_sign(
                AllTimePayActEnum.ACT_PAY_DO,
                "custo1", service_id,
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
            "PAY_ACCOUNT": "custo1",
            "SIGN": _make_sign(
                AllTimePayActEnum.ACT_VIEW_INFO,
                "custo1", "", "", self.pay_system.secret
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
            telephone="+797812345678"
        )
        # customer for tests
        custo1 = Customer.objects.create_user(
            telephone="+79782345678",
            username="129386",
            password="passw"
        )
        custo1.balance = -13.12
        custo1.fio = "Test Name"
        custo1.save(update_fields=("balance", "fio"))
        custo1.refresh_from_db()
        self.customer = custo1

        # RNCB Pay system
        pay_system = models_rncb.PayRNCBGateway.objects.create(
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
            "query_type": 'check',
            "account": "129386",
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<checkresponse>"
            "<fio>Test Name</fio>"
            "<balance>13.120000</balance>"
            "<error>0</error>"
            "<comments>Ok</comments>"
            "</checkresponse>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertXMLEqual(r.content.decode("utf-8"), xml)

    def test_pay_view_unknown_account(self):
        r = self.get(self.url, {
            "query_type": 'check',
            "account": "12089",
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<checkresponse>"
            "<error>1</error>"
            "<comments>Customer does not exists</comments>"
            "</checkresponse>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertXMLEqual(r.content.decode("utf-8"), xml)

    def test_pay_view_bad_account(self):
        r = self.get(self.url, {
            "query_type": 'check',
            "account": "*7867^&a",
        })
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, msg=r.data)

    def test_pay(self):
        r = self.get(self.url, {
            "query_type": 'pay',
            "account": "129386",
            "payment_id": 12983,
            "summa": 198.123321,
            "exec_date": "20170101182810",
            "inn": 1234567891
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<payresponse>"
            "<out_payment_id>1</out_payment_id>"
            "<error>0</error>"
            "<comments>Success</comments>"
            "</payresponse>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.assertXMLEqual(r.content.decode("utf-8"), xml)

    def test_pay_already_provided(self):
        now = datetime.now()
        pay = models_rncb.RNCBPayLog.objects.create(
            customer=self.customer,
            pay_id=1927863123,
            acct_time=now,
            amount=12.344,
            pay_gw=self.pay_system
        )
        r = self.get(self.url, {
            "query_type": 'pay',
            "account": "129386",
            "payment_id": 1927863123,
            "summa": 198.123321,
            "exec_date": "20170101182810",
            "inn": 1234567891
        })
        xml = ''.join((
            '<?xml version="1.0" encoding="utf-8"?>\n',
            "<payresponse>",
            "<out_payment_id>%d</out_payment_id>" % pay.pk,
            "<error>10</error>",
            "<comments>Payment duplicate</comments>",
            "</payresponse>"
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
            password="passw"
        )
        custo1.balance = -13.12
        custo1.fio = "Test Name"
        custo1.save(update_fields=("balance", "fio"))
        custo1.refresh_from_db()
        self.customer = custo1

        # RNCB Pay system
        pay_system = models_rncb.PayRNCBGateway.objects.create(
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
            models_rncb.RNCBPayLog(
                customer=self.customer,
                pay_id=12837,
                acct_time=now,
                amount=1,
                pay_gw=self.pay_system
            ),
            models_rncb.RNCBPayLog(
                customer=self.customer,
                pay_id=12838,
                acct_time=now + timedelta(days=2),
                amount=2,
                pay_gw=self.pay_system
            ),
            models_rncb.RNCBPayLog(
                customer=self.customer,
                pay_id=12839,
                acct_time=now + timedelta(days=6),
                amount=3,
                pay_gw=self.pay_system
            ),
            models_rncb.RNCBPayLog(
                customer=self.customer,
                pay_id=12840,
                acct_time=now + timedelta(days=8),
                amount=5,
                pay_gw=self.pay_system
            )
        ]
        models_rncb.RNCBPayLog.objects.bulk_create(logs)

    def test_pay_balance_check(self):
        r = self.get(self.url, {
            "query_type": 'balance',
            "datefrom": '20170101000000',
            "dateto": '2017012200000',
            #  "inn": 1234567891
        })
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<balanceresponse>"
              "<full_summa>11.000000</full_summa>"
              "<number_of_payments>4</number_of_payments>"
              "<error>0</error>"
              "<payments>"
                "<payment_row>12837;1;129386;3.00;20170101000000</payment_row>"
                "<payment_row>12838;2;129386;4.00;20170103000000</payment_row>"
                "<payment_row>12839;3;129386;5.00;20170107000000</payment_row>"
                "<payment_row>12840;4;129386;6.00;20170109000000</payment_row>"
              "</payments>"
            "</balanceresponse>"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.data)
        self.maxDiff = None
        self.assertXMLEqual(r.content.decode("utf-8"), xml)
