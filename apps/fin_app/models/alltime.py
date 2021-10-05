from datetime import datetime
from typing import Optional
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from django.db import models, connection
from rest_framework.exceptions import ParseError
from rest_framework.settings import api_settings
from encrypted_model_fields.fields import EncryptedCharField

from customers.models import Customer
from djing2.lib import safe_int
from djing2.models import BaseAbstractModel


class PayAllTimeGateway(BaseAbstractModel):
    title = models.CharField(_("Title"), max_length=64)
    secret = EncryptedCharField(verbose_name=_("Secret"), max_length=64)
    service_id = models.CharField(_("Service id"), max_length=64)
    slug = models.SlugField(_("Slug"), max_length=32, unique=True, allow_unicode=False)
    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "pay_all_time_gateways"
        verbose_name = _("All time gateway")


def report_by_pays(from_time: datetime, to_time: Optional[datetime] = None, pay_gw_id=None, group_by=0):
    group_by = safe_int(group_by)
    if group_by not in [1, 2, 3]:
        raise ParseError('Bad value in "group_by" param')

    params = [from_time]
    query = [
        "SELECT"
    ]
    date_fmt = getattr(api_settings, "DATETIME_FORMAT", "%Y-%m-%d %H:%M")
    if group_by == 1:
        # group by day
        query.append("date_trunc('day', date_add),")
        date_fmt = getattr(api_settings, "DATE_FORMAT", "%Y-%m-%d")
    elif group_by == 3:
        # group by mon
        query.append("date_trunc('month', date_add),")
        date_fmt = '%Y-%m'
    elif group_by == 2:
        # group by week
        query.append("date_trunc('week', date_add),")
        date_fmt = '%Y-%m'

    query.extend((
        'sum("sum") AS alsum,',
        'count("sum") as alcnt',
        "FROM all_time_pay_log",
        "where date_add >= %s::date",
    ))

    if pay_gw_id is not None:
        pay_gw_id = safe_int(pay_gw_id)
        if pay_gw_id > 0:
            query.append("and pay_gw_id = %s::integer")
            params.append(pay_gw_id)

    if to_time is not None:
        query.append("and date_add <= %s::date")
        params.append(to_time)

    query.extend((
        "group by 1",
        "order by 1",
    ))
    cur = connection.cursor()
    cur.execute(' '.join(query), params)

    while True:
        r = cur.fetchone()
        if r is None:
            break
        pay_time, summ, pay_count = r
        yield {
            'summ': round(summ, 4),
            'pay_date': pay_time.strftime(date_fmt),
            'pay_count': pay_count
        }


class AllTimePayLog(BaseAbstractModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_DEFAULT, blank=True, null=True, default=None)
    pay_id = models.CharField(max_length=36, unique=True, primary_key=True)
    date_add = models.DateTimeField(auto_now_add=True)
    sum = models.FloatField(_("Cost"), default=0.0)
    trade_point = models.CharField(_("Trade point"), max_length=20, default=None, null=True, blank=True)
    receipt_num = models.BigIntegerField(_("Receipt number"), default=0)
    pay_gw = models.ForeignKey(PayAllTimeGateway, verbose_name=_("Pay gateway"), on_delete=models.CASCADE)

    def __str__(self):
        return self.pay_id

    class Meta:
        db_table = "all_time_pay_log"
