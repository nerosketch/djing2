from functools import wraps
from ._general import cached_property
from datetime import datetime
from django.db import transaction
from django.db.models import Sum
from django.utils.encoding import force_str
from rest_framework.generics import GenericAPIView
from rest_framework_xml.renderers import XMLRenderer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from djing2.viewsets import DjingModelViewSet
from fin_app.models.rncb import PayRNCBGateway, RNCBPayLog
from fin_app.serializers import rncb as serializers_rncb
try:
    from customers.models import Customer
    from customers.tasks import customer_check_service_for_expiration
except ImportError as imperr:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        '"fin_app" application depends on "customers" '
        'application. Check if it installed'
    ) from imperr


class PayRNCBGatewayModelViewSet(DjingModelViewSet):
    queryset = PayRNCBGateway.objects.all()
    serializer_class = serializers_rncb.PayRNCBGatewayModelSerializer


class RNCBPayLogModelViewSet(DjingModelViewSet):
    queryset = RNCBPayLog.objects.all()
    serializer_class = serializers_rncb.RNCBPayLogModelSerializer


class DynamicRootXMLRenderer(XMLRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders `data` into serialized XML.
        """
        if data is None:
            return ""

        if isinstance(data, dict):
            if len(data.keys()) == 1:
                self.root_tag_name, val = next(i for i in data.items())
                data = val

        return super().render(
            data,
            accepted_media_type=accepted_media_type,
            renderer_context=renderer_context
        )

    def _to_xml(self, xml, data):
        if isinstance(data, (list, tuple)):
            for item in data:
                #  xml.startElement(self.item_tag_name, {})
                self._to_xml(xml, item)
                #  xml.endElement(self.item_tag_name)

        elif isinstance(data, dict):
            for key, value in data.items():
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)

        elif data is None:
            # Don't output any value
            pass

        else:
            xml.characters(force_str(data))


def payment_wrapper(request_serializer, response_serializer, root_tag: str):
    def _el(l: list):
        """Expand list"""
        return ' '.join(s for s in l)

    def _expand_str_from_err(err: ValidationError):
        if isinstance(err.detail, dict):
            return '\n'.join(f'{k}: {_el(v)}' for k, v in err.detail.items())
        return str(err.detail)

    def _fn(fn):
        @wraps(fn)
        def _wrapper(self, request, *args, **kwargs):
            try:
                ser = request_serializer(data=request.query_params)
                ser.is_valid(raise_exception=True)
                res = fn(self, data=ser.data, *args, **kwargs)
                r_ser = response_serializer(data=res)
                r_ser.is_valid(raise_exception=True)
                return Response({
                    root_tag: r_ser.data
                })
            except serializers_rncb.RNCBProtocolErrorException as e:
                return Response({root_tag: {
                    'ERROR': e.error,
                    'COMMENTS': _expand_str_from_err(e)
                }}, status=e.status_code)
            except ValidationError as e:
                return Response({root_tag: {
                    # 'CUSTOMER_NOT_FOUND' because RNCB wants it that way
                    'ERROR': serializers_rncb.RNCBPaymentErrorEnum.CUSTOMER_NOT_FOUND.value,
                    'COMMENTS': _expand_str_from_err(e)
                }}, status=status.HTTP_200_OK)
            except Customer.DoesNotExist:
                return Response({root_tag: {
                    'ERROR': serializers_rncb.RNCBPaymentErrorEnum.CUSTOMER_NOT_FOUND.value,
                    'COMMENTS': 'Customer does not exists'
                }}, status=status.HTTP_200_OK)

        return _wrapper
    return _fn


class RNCBPaymentViewSet(GenericAPIView):
    renderer_classes = [DynamicRootXMLRenderer]
    http_method_names = ["get"]
    queryset = PayRNCBGateway.objects.all()
    serializer_class = serializers_rncb.PayRNCBGatewayModelSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "pay_slug"
    permission_classes = [AllowAny]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        kw = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        return PayRNCBGateway.objects.get(**kw)

    @cached_property
    def _lazy_object(self):
        return self.get_object()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(sites__in=[self.request.site])

    def get(self, request, *args, **kwargs):
        query_type = request.query_params.get('QueryType')
        query_type_map = {
            'check': self._check,
            'pay': self._pay,
            'balance': self._balance,
        }
        query_m = query_type_map.get(query_type, self._unknown_query_type)
        return query_m(request, *args, **kwargs)

    @payment_wrapper(
        request_serializer=serializers_rncb.RNCBPaymentCheckSerializer,
        response_serializer=serializers_rncb.RNCBPaymentCheckResponseSerializer,
        root_tag='CHECKRESPONSE'
    )
    def _check(self, data: dict, *args, **kwargs):
        account = data['Account']

        customer = Customer.objects.filter(username=account)
        if hasattr(self.request, 'site'):
            customer = customer.filter(sites__in=[self.request.site])
        customer = customer.get()

        return {
            # 'fio': customer.get_full_name(),
            'BALANCE': f'{customer.balance:.2f}',
            'COMMENTS': 'Ok',
            #  'inn': ''
        }

    @payment_wrapper(
        request_serializer=serializers_rncb.RNCBPaymentPaySerializer,
        response_serializer=serializers_rncb.RNCBPaymentPayResponseSerializer,
        root_tag='PAYRESPONSE'
    )
    def _pay(self, data: dict, *args, **kwargs):
        account = data['Account']
        payment_id = data['Payment_id']
        pay_amount = float(data['Summa'])
        exec_date = data['Exec_date']
        if not isinstance(exec_date, datetime):
            exec_date = datetime.strptime(exec_date, serializers_rncb.date_format)
        #  inn = data['inn']

        customer = Customer.objects.filter(username=account, is_active=True)
        if hasattr(self.request, 'site'):
            customer = customer.filter(sites__in=[self.request.site])
        customer = customer.get()

        pay = RNCBPayLog.objects.filter(
            pay_id=payment_id
        ).first()
        if pay is not None:
            return {
                'ERROR': serializers_rncb.RNCBPaymentErrorEnum.DUPLICATE_TRANSACTION.value,
                'OUT_PAYMENT_ID': pay.pk,
                'COMMENTS': 'Payment duplicate'
            }
        del pay

        with transaction.atomic():
            customer.add_balance(
                profile=None,
                cost=pay_amount,
                comment=f"{self._lazy_object.title} {pay_amount:.2f}"
            )
            customer.save(update_fields=("balance",))
            log = RNCBPayLog.objects.create(
                customer=customer,
                pay_id=payment_id,
                acct_time=exec_date,
                amount=pay_amount,
                pay_gw=self._lazy_object
            )
        customer_check_service_for_expiration(customer_id=customer.pk)

        return {
            'OUT_PAYMENT_ID': log.pk,
            'COMMENTS': 'Success'
        }

    @payment_wrapper(
        request_serializer=serializers_rncb.RNCBPaymentTransactionCheckSerializer,
        response_serializer=serializers_rncb.RNCBPaymentTransactionCheckResponseSerializer,
        root_tag='BALANCERESPONSE'
    )
    def _balance(self, data: dict, *args, **kwargs):
        date_from = data['DateFrom']
        date_to = data['DateTo']
        #  inn = data['inn']

        date_from = datetime.strptime(date_from, serializers_rncb.date_format)
        date_to = datetime.strptime(date_to, serializers_rncb.date_format)

        pays = RNCBPayLog.objects.filter(
            acct_time__gte=date_from,
            acct_time__lte=date_to
        ).select_related('customer').order_by('id')

        def _gen_pay(p: RNCBPayLog):
            return {
                'PAYMENT_ROW': '%(payment_id)d;%(out_payment_id)d;%(account)s;%(sum).2f;%(ex_date)s' % {
                    'payment_id': p.pay_id,
                    'out_payment_id': p.pk,
                    'account': p.customer.username,
                    'sum': float(p.amount),
                    'ex_date': p.acct_time.strftime(serializers_rncb.date_format)
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

    def _unknown_query_type(self, *args, **kwargs):
        return Response('Unknown QueryType parameter', status=status.HTTP_400_BAD_REQUEST)

