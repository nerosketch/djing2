from typing import Type
from decimal import Decimal
from functools import wraps
from enum import Enum
from datetime import datetime

from django.contrib.sites.models import Site
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.utils import get_object_or_404

from django.db import transaction
from django.db.models import Sum
from starlette import status
from pydantic import BaseModel, ValidationError
from fastapi import APIRouter, Depends, Path, Query, Request, Response
from dicttoxml import dicttoxml

from fin_app.models.base_payment_model import fetch_customer_profile
from fin_app.models.rncb import RNCBPaymentGateway, RNCBPaymentLog
from fin_app import custom_signals
from fin_app.schemas import rncb as schemas

try:
    from customers.models import Customer
except ImportError as imperr:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        '"fin_app" application depends on "customers" '
        'application. Check if it installed'
    ) from imperr


router = APIRouter(
    prefix='/rncb',
)


router.include_router(
    CrudRouter(
        schema=schemas.RNCBPayLogModelSchema,
        queryset=RNCBPaymentLog.objects.all()
    ),
    prefix='/log',
    dependencies=[Depends(is_admin_auth_dependency)],
)


def payment_wrapper(request_schema: Type[BaseModel], response_schema: Type[BaseModel], root_tag: str):
    def _el(lst: list):
        """Expand list"""
        return ' '.join(s for s in lst)

    def _expand_str_from_err(err):
        if isinstance(err, dict):
            return '\n'.join(f'{k}: {_el(v)}' for k, v in err.items())
        return str(err)

    def _fn(fn):
        @wraps(fn)
        def _wrapper(request: Request, pay_gateway: RNCBPaymentGateway, curr_site: Site):
            try:
                data = dict(request.query_params)
                request_schema(**data)

                res = fn(data=data, pay_gateway=pay_gateway, curr_site=curr_site)
                r_schema = response_schema(res)
                return Response(dicttoxml({
                    root_tag: r_schema.dict()
                }), media_type='text/xml')
            except schemas.RNCBProtocolErrorException as e:
                return Response(
                    dicttoxml({root_tag: {
                        'ERROR': e.error.value,
                        'COMMENTS': _expand_str_from_err(e.detail)
                    }}),
                    status_code=e.status_code,
                    media_type='text/xml'
                )
            except ValidationError as e:
                return Response(
                    dicttoxml({root_tag: {
                        'ERROR': schemas.RNCBPaymentErrorEnum.CUSTOMER_NOT_FOUND.value,
                        'COMMENTS': _expand_str_from_err(e)
                    }}),
                    status_code=status.HTTP_200_OK,
                    media_type='text/xml'
                )
            except Customer.DoesNotExist:
                return Response(
                    dicttoxml({root_tag: {
                        'ERROR': schemas.RNCBPaymentErrorEnum.CUSTOMER_NOT_FOUND.value
                        'COMMENTS': 'Customer does not exists'
                    }}),
                    status_code=status.HTTP_200_OK,
                    media_type='text/xml'
                )

        return _wrapper
    return _fn


class QueryTypeEnum(str, Enum):
    CHECK = 'check'
    PAY = 'pay'
    BALANCE = 'balance'


@payment_wrapper(
    request_schema=schemas.RNCBPaymentCheckSchema,
    response_schema=schemas.RNCBPaymentCheckResponseSchema,
    root_tag='CHECKRESPONSE'
)
def _check(data: dict, pay_gateway: RNCBPaymentGateway, curr_site: Site):
    account = data['Account']
    customer = fetch_customer_profile(
        curr_site=curr_site,
        username=account
    )

    return {
        # 'fio': customer.get_full_name(),
        'BALANCE': f'{customer.balance:.2f}',
        'COMMENTS': 'Ok',
        #  'inn': ''
    }


@payment_wrapper(
    request_schema=schemas.RNCBPaymentPaySchema,
    response_schema=schemas.RNCBPaymentPayResponseSchema,
    root_tag='PAYRESPONSE'
)
def _pay(data: dict, pay_gateway: RNCBPaymentGateway, curr_site: Site):
    account = data['account']
    payment_id = data['payment_id']
    pay_amount = float(data['summa'])
    exec_date = data['exec_date']
    if not isinstance(exec_date, datetime):
        exec_date = datetime.strptime(exec_date, schemas.date_format)
    #  inn = data['inn']

    customer = fetch_customer_profile(
        curr_site=curr_site,
        username=account
    )

    pay = RNCBPaymentLog.objects.filter(
        pay_id=payment_id
    ).first()
    if pay is not None:
        return {
            'ERROR': schemas.RNCBPaymentErrorEnum.DUPLICATE_TRANSACTION.value,
            'OUT_PAYMENT_ID': pay.pk,
            'COMMENTS': 'Payment duplicate'
        }
    del pay

    custom_signals.before_payment_success.send(
        sender=Customer,
        instance=customer,
        amount=Decimal(pay_amount)
    )
    with transaction.atomic():
        customer.add_balance(
            profile=None,
            cost=Decimal(pay_amount),
            comment=f"{pay_gateway.title} {pay_amount:.2f}"
        )
        log = RNCBPaymentLog.objects.create(
            customer=customer,
            pay_id=payment_id,
            acct_time=exec_date,
            amount=pay_amount,
            pay_gw=pay_gateway
        )
    custom_signals.after_payment_success.send(
        sender=Customer,
        instance=customer,
        amount=Decimal(pay_amount)
    )

    return {
        'OUT_PAYMENT_ID': log.pk,
        'COMMENTS': 'Success'
    }


@payment_wrapper(
    request_schema=schemas.RNCBPaymentTransactionCheckSchema,
    response_schema=schemas.RNCBPaymentTransactionCheckResponseSchema,
    root_tag='BALANCERESPONSE'
)
def _balance(data: dict, pay_gateway: RNCBPaymentGateway, curr_site: Site):
    date_from = data['date_from']
    date_to = data['date_to']
    #  inn = data['inn']

    date_from = datetime.strptime(date_from, schemas.date_format)
    date_to = datetime.strptime(date_to, schemas.date_format)

    pays = RNCBPaymentLog.objects.filter(
        acct_time__gte=date_from,
        acct_time__lte=date_to
    ).select_related('customer').order_by('id')

    def _gen_pay(p: RNCBPaymentLog):
        return {
            'PAYMENT_ROW': '%(payment_id)d;%(out_payment_id)d;%(account)s;%(sum).2f;%(ex_date)s' % {
                'payment_id': p.pay_id,
                'out_payment_id': p.pk,
                'account': p.customer.username,
                'sum': float(p.amount),
                'ex_date': p.acct_time.strftime(schemas.date_format)
            }
        }

    fs = pays.aggregate(Sum('amount'))
    full_sum = fs.get('amount__sum', 0.0)
    del fs
    return {
        'FULL_SUMMA': f'{full_sum or 0.0:.2f}',
        'NUMBER_OF_PAYMENTS': pays.count(),
        'PAYMENTS': [_gen_pay(p) for p in pays]
    }


def _unknown_query_type(data: dict, pay_gateway: RNCBPaymentGateway, curr_site: Site):
    return Response(
        'Unknown QueryType parameter',
        status_code=status.HTTP_400_BAD_REQUEST
    )


query_type_map = {
    QueryTypeEnum.CHECK: _check,
    QueryTypeEnum.PAY: _pay,
    QueryTypeEnum.BALANCE: _balance,
}


@router.get('/{pay_slug}/pay/', response_class=XmlTextResponse)
def rncb_payment_route(
    request: Request,
    pay_slug: str = Path(
        title='Payment gateway name',
        max_length=32,
        regex=r'^[-a-zA-Z0-9_]+\Z'
    ),
    query_type: QueryTypeEnum = Query(alias='QueryType'),
    curr_site: Site = Depends(sites_dependency),
) -> Response:
    qs = RNCBPaymentGateway.objects.filter(sites__in=[curr_site])
    pay_gateway = get_object_or_404(qs, slug=pay_slug)

    query_m = query_type_map.get(query_type, _unknown_query_type)

    return query_m(
        request=request,
        pay_gateway=pay_gateway,
        curr_site=curr_site
    )


router.route_class = NonJsonRoute
add_openapi_extension(router)


router.include_router(CrudRouter(
    schema=schemas.PayRNCBGatewayModelSchema,
    queryset=RNCBPaymentGateway.objects.all()
), dependencies=[Depends(is_admin_auth_dependency)])
