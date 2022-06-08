import os
from pathlib import Path
from datetime import datetime
from django.test import override_settings
from django.contrib.sites.models import Site
from fin_app.models.alltime import PayAllTimeGateway
from customers.tests.customer import CustomAPITestCase
from .test_ftp_server import FtpTest, FtpTestCaseMixin
from sorm_export.hier_export.base import format_fname
from sorm_export.models import datetime_format
from fin_app.views.alltime import AllTimePayActEnum
from fin_app.tests import _make_sign


@override_settings(
    DEFAULT_FTP_CREDENTIALS={
        "host": '127.0.0.1',
        "uname": 'testuname',
        "password": 'testpassw',
        "port": 2122
    },
    SORM_EXPORT_FTP_DISABLE=False
)
class PaymentsExportAPITestCase(CustomAPITestCase, FtpTestCaseMixin):
    payment_url = "/api/fin/alltime/asd/pay/"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ftp_test = FtpTest()
        ftp_test.start()
        cls.ftp_test = ftp_test

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.ftp_test.release()

    def setUp(self):
        super().setUp()
        example_site = Site.objects.first()
        gw = PayAllTimeGateway.objects.create(
            title='asd',
            secret='secretasd',
            service_id='serviceasd',
            slug='asd',
        )
        gw.sites.add(example_site)
        gw.refresh_from_db()
        self.gw = gw

    def _make_customer_pay(self):
        service_id = str(self.gw.service_id)
        self.get(
            self.payment_url,
            {
                "ACT": AllTimePayActEnum.ACT_PAY_DO.value,
                "PAY_ACCOUNT": self.customer.username,
                "PAY_AMOUNT": 12,
                "RECEIPT_NUM": 127468,
                "SERVICE_ID": service_id,
                "PAY_ID": "840ab457-e7d1-4494-8197-9570da035170",
                "TRADE_POINT": "term1",
                "SIGN": _make_sign(
                    AllTimePayActEnum.ACT_PAY_DO,
                    str(self.customer.username), service_id,
                    "840ab457-e7d1-4494-8197-9570da035170",
                    str(self.gw.secret)
                ),
            },
        )

    def test_customer_payment_task(self):
        Path('/tmp/ISP/abonents').mkdir(parents=True, exist_ok=True)
        event_time = datetime.now()
        fname = f"/tmp/ISP/abonents/payments_v1_{format_fname(event_time)}.txt"

        self._make_customer_pay()

        pay_time_str = event_time.strftime(datetime_format)
        self.assertFtpFile(
            fname=fname,
            content=''.join((
                f'"{self.customer.pk}";"";"{pay_time_str}";"12.00";"Безналичный";',
                '"платёжная система \'24 All Time\', ',
                'Идентификатор торговой точки: \'term1\'. Номер чека, ',
                'выдаваемого клиенту: \'127468\'."'
            ))
        )
        os.remove(fname)

