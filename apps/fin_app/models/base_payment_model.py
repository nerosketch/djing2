from datetime import datetime
from typing import Optional, Type
from django.utils.translation import gettext_lazy as _
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.contrib.sites.models import Site
from rest_framework.exceptions import ParseError
from django.db import models
from djing2.lib import safe_int
from djing2.models import BaseAbstractModel
try:
    from customers.models import Customer
except ImportError as imperr:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        '"fin_app" application depends on "customers" '
        'application. Check if it installed'
    ) from imperr


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


def report_by_pays(from_time: Optional[datetime], to_time: Optional[datetime] = None,
        pay_gw_id=None, group_by=0, limit=50):
    group_by = safe_int(group_by)
    if not group_by:
        raise ParseError('Bad value in "group_by" param')

    if not from_time:
        raise ParseError('from_time is required')

    flds = {
        1: {
            # group by day
            'field': "date_trunk",
            'annotate': {'date_trunk': TruncDay('date_add', output_field=models.DateField())}
        },
        2: {
            # group by week
            'field': "date_trunk",
            'annotate': {'date_trunk': TruncWeek('date_add', output_field=models.DateField())}
        },
        3: {
            # group by mon
            'field': "date_trunk",
            'annotate': {'date_trunk': TruncMonth('date_add', output_field=models.DateField())}
        },
        4: {
            # group by customers
            'field': "customer__fio",
            'related_fields': ['customer__username', 'customer__fio']
        },
    }

    query_opt = flds.get(group_by)
    if query_opt is None:
        raise ParseError('Bad value in "group_by" param')

    field_name = query_opt['field']
    annotation = query_opt.get('annotate', {})

    qs = BasePaymentLogModel.objects.filter(
        date_add__gte=from_time
    )
    related_fields = query_opt.get('related_fields', [])

    qs = qs.annotate(**annotation).values(
        *([field_name] + related_fields)
    ).annotate(
        summ=models.Sum('amount'),
        pay_count=models.Count('amount'),
    )

    if pay_gw_id is not None:
        pay_gw_id = safe_int(pay_gw_id)
        if pay_gw_id > 0:
            qs = qs.filter(pay_gw_id=pay_gw_id)

    if to_time is not None:
        qs = qs.filter(date_add__lte=to_time)

    for item in qs[:limit].iterator():
        yield {
            'summ': item['summ'],
            'pay_count': item['pay_count'],
            **{field_name: item[field_name]},
            **{f:item[f] for f in related_fields}
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


def get_payment_types() -> list[tuple[int, str]]:
    return _payment_types


def fetch_customer_profile(request, username: str) -> Customer:
    customer = Customer.objects.filter(username=username, is_active=True)
    if hasattr(request, 'site'):
        customer = customer.filter(sites__in=[request.site])
    return customer.get()
