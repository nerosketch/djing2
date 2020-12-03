from hashlib import md5

from django.db import transaction
from django.db.utils import DatabaseError
from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_xml.renderers import XMLRenderer

from customers.models import Customer
from customers.tasks import customer_check_service_for_expiration
from djing2.lib import safe_int, safe_float
from djing2.viewsets import DjingModelViewSet
from fin_app import serializers
from fin_app.models import AllTimePayLog, PayAllTimeGateway


class AllTimeGatewayModelViewSet(DjingModelViewSet):
    queryset = PayAllTimeGateway.objects.annotate(
        pay_count=Count('alltimepaylog')
    )
    serializer_class = serializers.AllTimeGatewayModelSerializer

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )


class AllTimePayLogModelViewSet(DjingModelViewSet):
    queryset = AllTimePayLog.objects.all()
    serializer_class = serializers.AllTimePayLogModelSerializer


class AllTimeSpecifiedXMLRenderer(XMLRenderer):
    root_tag_name = 'pay-response'


class AllTimePay(GenericAPIView):
    http_method_names = 'get',
    renderer_classes = AllTimeSpecifiedXMLRenderer,
    queryset = PayAllTimeGateway.objects.all()
    serializer_class = serializers.PayAllTimeGatewayModelSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'pay_slug'
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    _obj_cache = None

    @property
    def _lazy_object(self):
        if self._obj_cache is None:
            self._obj_cache = self.get_object()
        self.object = self._obj_cache
        return self.object

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(sites__in=[self.request.site])

    @staticmethod
    def _bad_ret(err_id: int, err_description: str=None) -> Response:
        now = timezone.now()
        r = {
            'status_code': safe_int(err_id),
            'time_stamp': now.strftime("%d.%m.%Y %H:%M")
        }
        if err_description:
            r.update({'description': err_description})
        return Response(r)

    def check_sign(self, data: dict, sign: str) -> bool:
        act: int = safe_int(data.get('ACT'))
        pay_account = data.get('PAY_ACCOUNT')
        serv_id = data.get('SERVICE_ID')
        pay_id = data.get('PAY_ID')
        md = md5()
        s = '_'.join(
            (str(act), pay_account or '', serv_id or '',
             pay_id or '', self._lazy_object.secret)
        )
        md.update(bytes(s, 'utf-8'))
        our_sign = md.hexdigest()
        return our_sign == sign

    def get(self, request, *args, **kwargs):
        act: int = safe_int(request.GET.get('ACT'))
        self.current_date = timezone.now().strftime("%d.%m.%Y %H:%M")

        if act <= 0:
            return self._bad_ret(-101, 'ACT must be more than 0')
        sign = request.GET.get('SIGN')
        if not sign:
            return self._bad_ret(-101, 'SIGN not passed')
        if not self.check_sign(request.GET, sign.lower()):
            return self._bad_ret(-101, 'Bad sign')

        try:
            if act == 1:
                return self._fetch_user_info(request.GET)
            elif act == 4:
                return self._make_pay(request.GET)
            elif act == 7:
                return self._check_pay(request.GET)
            else:
                return self._bad_ret(-101, 'ACT is not passed')
        except Customer.DoesNotExist:
            return self._bad_ret(-40, 'Account does not exist')
        except PayAllTimeGateway.DoesNotExist:
            return self._bad_ret(-40, 'Pay gateway does not exist')
        except DatabaseError:
            return self._bad_ret(-90)
        except AllTimePayLog.DoesNotExist:
            return self._bad_ret(-10)
        except AttributeError:
            return self._bad_ret(-101)

    def _fetch_user_info(self, data: dict) -> Response:
        pay_account = data.get('PAY_ACCOUNT')
        customer = Customer.objects.get(username=pay_account)
        return Response({
            'balance': round(customer.balance, 2),
            'name': customer.fio,
            'account': pay_account,
            'service_id': self._lazy_object.service_id,
            'min_amount': 10.0,
            'max_amount': 15000,
            'status_code': 21,
            'time_stamp': self.current_date
        })

    def _make_pay(self, data: dict) -> Response:
        trade_point = safe_int(data.get('TRADE_POINT'))
        receipt_num = safe_int(data.get('RECEIPT_NUM'))
        pay_account = data.get('PAY_ACCOUNT')
        pay_id = data.get('PAY_ID')
        pay_amount = safe_float(data.get('PAY_AMOUNT'))
        customer = Customer.objects.get(username=pay_account)
        pays = AllTimePayLog.objects.filter(pay_id=pay_id)
        if pays.exists():
            return self._bad_ret(-100, 'Pay already exists')

        with transaction.atomic():
            customer.add_balance(
                profile=None,
                cost=pay_amount,
                comment='%s %.2f' % (self._lazy_object.title, pay_amount)
            )
            customer.save(update_fields=('balance',))

            AllTimePayLog.objects.create(
                customer=customer,
                pay_id=pay_id,
                sum=pay_amount,
                trade_point=trade_point,
                receipt_num=receipt_num,
                pay_gw=self._lazy_object
            )
        customer_check_service_for_expiration(
            customer_id=customer.pk
        )
        return Response({
            'pay_id': pay_id,
            'service_id': data.get('SERVICE_ID'),
            'amount': round(pay_amount, 2),
            'status_code': 22,
            'time_stamp': self.current_date
        })

    def _check_pay(self, data: dict) -> Response:
        pay_id = data.get('PAY_ID')
        pay = AllTimePayLog.objects.get(pay_id=pay_id)
        return Response({
            'status_code': 11,
            'time_stamp': self.current_date,
            'transaction': {
                'pay_id': pay_id,
                'service_id': data.get('SERVICE_ID'),
                'amount': round(pay.sum, 2),
                'status': 111,
                'time_stamp': pay.date_add.strftime("%d.%m.%Y %H:%M")
            }
        })
