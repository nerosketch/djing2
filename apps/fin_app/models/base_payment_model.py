from datetime import datetime
from typing import Optional, List, Tuple, Type
from django.utils.translation import gettext_lazy as _
from django.db import models, connection
from django.contrib.sites.models import Site
from rest_framework.exceptions import ParseError
from rest_framework.settings import api_settings
from djing2.lib import safe_int
from djing2.models import BaseAbstractModel
from customers.models import Customer


_payment_types = [
    (0, _('Unknown'))
]


class BasePaymentModel(BaseAbstractModel):
    pay_system_title = "Base abstract implementation"

    payment_type = models.PositiveSmallIntegerField(default=0, choices=_payment_types)
    title = models.CharField(_("Title"), max_length=64)
    slug = models.SlugField(_("Slug"), max_length=32, allow_unicode=False)
    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "base_payment_gateway"
        verbose_name = _("Base gateway")
        unique_together = ('slug', 'title')
        #  abstract = True


def report_by_pays(from_time: Optional[datetime], to_time: Optional[datetime] = None, pay_gw_id=None, group_by=0):
    group_by = safe_int(group_by)
    if not group_by:
        raise ParseError('Bad value in "group_by" param')

    if not from_time:
        raise ParseError('from_time is required')

    flds = {
        1: {
            # group by day
            'query': "date_trunc('day', date_add),",
            'format_fn': lambda val: val.strftime('%Y-%m-%d')
        },
        2: {
            # group by week
            'query': "date_trunc('week', date_add),",
            'format_fn': lambda val: val.strftime('%Y-%m')
        },
        3: {
            # group by mon
            'query': "date_trunc('month', date_add),",
            'format_fn': lambda val: val.strftime('%Y-%m')
        },
        4: {
            # group by customers
            'query': "customer_id,",
        },
    }

    params = [from_time]
    query = [
        "SELECT"
    ]

    query_opt = flds.get(group_by)
    if query_opt is None:
        raise ParseError('Bad value in "group_by" param')

    query.append(query_opt['query'])

    query.extend((
        "SUM(amount) AS alsum,",
        "COUNT(amount) AS alcnt",
        "FROM base_payment_log",
        "WHERE date_add >= %s::date",
    ))

    if pay_gw_id is not None:
        pay_gw_id = safe_int(pay_gw_id)
        if pay_gw_id > 0:
            query.append("AND pay_gw_id = %s::integer")
            params.append(pay_gw_id)

    if to_time is not None:
        query.append("AND date_add <= %s::date")
        params.append(to_time)

    query.extend((
        "GROUP BY 1",
        "ORDER BY 1",
    ))
    cur = connection.cursor()
    cur.execute(' '.join(query), params)

    def _default_format(val):
        return val

    while True:
        r = cur.fetchone()
        if r is None:
            break
        report_data, summ, pay_count = r
        yield {
            'data': {
                'val': query_opt.get('format_fn', _default_format)(report_data),
                'name': 'date'
            },
            'summ': round(summ, 4),
            'pay_count': pay_count
        }


class BasePaymentLogModel(BaseAbstractModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_DEFAULT,
        blank=True, null=True, default=None
    )
    pay_gw = models.ForeignKey(
        BasePaymentModel,
        verbose_name=_("Pay gateway"),
        on_delete=models.CASCADE
    )
    date_add = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(
        _("Cost"),
        default=0.0,
        max_digits=19,
        decimal_places=6
    )

    class Meta:
        db_table = 'base_payment_log'
        verbose_name = _("Base payment log")
        #  abstract = True


def add_payment_type(code: int, gateway_model: Type[BasePaymentModel]):
    global _payment_types
    _payment_types.append((code, gateway_model.pay_system_title))


def get_payment_types() -> List[Tuple[int, str]]:
    return _payment_types

