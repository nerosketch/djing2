from functools import wraps
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


class RNCBCheckResponseXMLRenderer(XMLRenderer):
    root_tag_name = "CHECKRESPONSE"


class RNCBPayResponseXMLRenderer(XMLRenderer):
    root_tag_name = "PAYRESPONSE"


class RNCBBalanceResponseXMLRenderer(XMLRenderer):
    root_tag_name = "BALANCERESPONSE"


def payment_wrapper(request_serializer, response_serializer, renderer_class):
    def _fn(fn):
        @wraps(fn)
        def _wrapper(self, request, *args, **kwargs):
            self.renderer_classes = [renderer_class]
            try:
                ser = request_serializer(data=request.query_params)
                ser.is_valid(raise_exception=True)
                res = fn(data=ser.data, *args, **kwargs)
                r_ser = response_serializer(data=res)
                r_ser.is_valid(raise_exception=True)
                return Response(r_ser.data)
            except serializers_rncb.RNCBProtocolErrorExeption as e:
                return Response({
                    'error': e.error,
                    'comments': str(e)
                }, status=e.status_code)
            except ValidationError as e:
                return Response({
                    'error': serializers_rncb.RNCBPaymentErrorEnum,
                    'comments': str(e)
                }, status=e.status_code)
            except Customer.DoesNotExists:
                raise serializers_rncb.RNCBProtocolErrorExeption(
                    'Customer does not exists',
                    error=serializers_rncb.RNCBPaymentErrorEnum.CUSTOMER_NOT_FOUND
                )

        return _wrapper
    return _fn


class RNCBPaymentViewSet(GenericAPIView):
    http_method_names = ["get"]
    queryset = PayRNCBGateway.objects.all()
    serializer_class = serializers_rncb.PayRNCBGatewayModelSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "pay_slug"
    permission_classes = [AllowAny]

    @property
    def _lazy_object(self):
        if self._obj_cache is None:
            self._obj_cache = self.get_object()
        self.object = self._obj_cache
        return self.object

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
        renderer_class=RNCBCheckResponseXMLRenderer
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
        renderer_class=RNCBPayResponseXMLRenderer
    )
    def _pay(self, data: dict, *args, **kwargs):
        account = data['account']
        payment_id = data['payment_id']
        pay_amount = data['summa']
        exec_date = data['exec_date']
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
                'error': serializers_rncb.RNCBPaymentErrorEnum.DUPLICATE_TRANSACTION,
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
        renderer_class=RNCBBalanceResponseXMLRenderer,
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

