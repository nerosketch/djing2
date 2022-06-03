from functools import wraps, cached_property
from datetime import datetime
from django.db import transaction
from django.db.models import Sum
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


def payment_wrapper(request_serializer, response_serializer, root_tag: str):
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
                    'error': e.error,
                    'comments': str(e)
                }}, status=e.status_code)
            except ValidationError as e:
                return Response({root_tag: {
                    'error': serializers_rncb.RNCBPaymentErrorEnum.UNKNOWN_CODE.value,
                    'comments': str(e)
                }}, status=e.status_code)
            except Customer.DoesNotExist:
                return Response({root_tag: {
                    'error': serializers_rncb.RNCBPaymentErrorEnum.CUSTOMER_NOT_FOUND.value,
                    'comments': 'Customer does not exists'
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
        query_type = request.query_params.get('query_type')
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
        root_tag='checkresponse'
    )
    def _check(self, data: dict, *args, **kwargs):
        account = data['account']

        customer = Customer.objects.get(username=account)

        return {
            'fio': customer.get_full_name(),
            'balance': -customer.balance,
            'comments': 'Ok',
            #  'inn': ''
        }

    @payment_wrapper(
        request_serializer=serializers_rncb.RNCBPaymentPaySerializer,
        response_serializer=serializers_rncb.RNCBPaymentPayResponseSerializer,
        root_tag='payresponse'
    )
    def _pay(self, data: dict, *args, **kwargs):
        account = data['account']
        payment_id = data['payment_id']
        pay_amount = float(data['summa'])
        exec_date = data['exec_date']
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
                'error': serializers_rncb.RNCBPaymentErrorEnum.DUPLICATE_TRANSACTION.value,
                'out_payment_id': pay.pk,
                'comments': 'Payment duplicate'
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
            'out_payment_id': log.pk,
            'comments': 'Success'
        }

    @payment_wrapper(
        request_serializer=serializers_rncb.RNCBPaymentTransactionCheckSerializer,
        response_serializer=serializers_rncb.RNCBPaymentTransactionCheckResponseSerializer,
        root_tag='balanceresponse'
    )
    def _balance(self, data: dict, *args, **kwargs):
        date_from = data['datefrom']
        date_to = data['dateto']
        #  inn = data['inn']

        pays = RNCBPayLog.objects.filter(
            acct_time__lte=date_from,
            acct_time__gte=date_to
        ).select_related('customer')
        #.annotate(all_sum=Sum('amount'), )

        def _gen_pay(p: RNCBPayLog):
            return {
                'payment_row': '%(payment_id)d;%(out_payment_id)d;%(account)s;%(sum).2f;%(ex_date)s' % {
                    'payment_id': p.pay_id,
                    'out_payment_id': p.pk,
                    'account': p.customer.username,
                    'sum': float(p.amount),
                    'ex_date': p.acct_time
                }
            }


        return {
            'full_summa': pays.aggregate(Sum('amount')),
            'number_of_payments': pays.count(),
            'payments': (_gen_pay(p) for p in pays.iterator())
        }

    def _unknown_query_type(self, *args, **kwargs):
        return Response('Unknown QueryType parameter', status=status.HTTP_400_BAD_REQUEST)

