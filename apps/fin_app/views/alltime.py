from hashlib import md5
from enum import IntEnum

from django.db import transaction
from django.db.utils import DatabaseError
from django.db.models import Count
from django.http import Http404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_xml.renderers import XMLRenderer

try:
    from customers.models import Customer
    from customers.tasks import customer_check_service_for_expiration
except ImportError as imperr:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        '"fin_app" application depends on "customers" '
        'application. Check if it installed'
    ) from imperr

from djing2.lib import safe_int, safe_float
from djing2.viewsets import DjingModelViewSet
from fin_app.serializers import alltime as alltime_serializers
from fin_app.models.alltime import AllTimePayLog, PayAllTimeGateway, report_by_pays


class CustomIntEnum(IntEnum):
    @classmethod
    def in_range(cls, value: int):
        return value in cls._value2member_map_


class AllTimePayActEnum(CustomIntEnum):
    ACT_VIEW_INFO = 1
    ACT_PAY_DO = 4
    ACT_PAY_CHECK = 7


class AllTimeStatusCodeEnum(CustomIntEnum):
    PAYMENT_OK = 22
    PAYMENT_POSSIBLE = 21
    TRANSACTION_STATUS_DETERMINED = 11
    TRANSACTION_NOT_FOUND = -10
    CUSTOMER_NOT_FOUND = -40
    PAYMENT_IS_DENIED_FOR_CUSTOMER = -41
    PAYMENT_ON_THIS_SUM_FOR_CUSTOMER_IS_NOT_ALLOWED = -42
    SERVICE_UNAVIALABLE = -90
    MORE_THAN_ONE_PAYMENTS = -100
    BAD_REQUEST = -101


TRANSACTION_STATUS_PAYMENT_OK = 111
# TRANSACTION_STATUS_PAYMENT_IN_PROCESS = 120
# TRANSACTION_STATUS_PAYMENT_CANCELLED = 130


class AllTimeGatewayModelViewSet(DjingModelViewSet):
    queryset = PayAllTimeGateway.objects.annotate(pay_count=Count("alltimepaylog"))
    serializer_class = alltime_serializers.AllTimeGatewayModelSerializer

    @action(methods=['get'], detail=False)
    def pays_report(self, request):
        ser = alltime_serializers.PaysReportParamsSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        dat = ser.data
        r = report_by_pays(
            from_time=dat.get('from_time'),
            to_time=dat.get('to_time'),
            pay_gw_id=dat.get('pay_gw'),
            group_by=dat.get('group_by', 0),
        )
        return Response(tuple(r))

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )


class AllTimePayLogModelViewSet(DjingModelViewSet):
    queryset = AllTimePayLog.objects.all()
    serializer_class = alltime_serializers.AllTimePayLogModelSerializer


class AllTimeSpecifiedXMLRenderer(XMLRenderer):
    root_tag_name = "pay-response"


class AllTimePay(GenericAPIView):
    http_method_names = ("get",)
    renderer_classes = (AllTimeSpecifiedXMLRenderer,)
    queryset = PayAllTimeGateway.objects.all()
    serializer_class = alltime_serializers.PayAllTimeGatewayModelSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "pay_slug"
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
    def _bad_ret(err_id: AllTimeStatusCodeEnum, err_description: str = None) -> Response:
        now = timezone.now()
        r = {
            "status_code": safe_int(err_id.value),
            "time_stamp": now.strftime("%d.%m.%Y %H:%M")
        }
        if err_description:
            r.update({"description": err_description})
        return Response(r)

    def check_sign(self, data: dict, sign: str) -> bool:
        act: int = safe_int(data.get("ACT"))
        pay_account = data.get("PAY_ACCOUNT")
        serv_id = data.get("SERVICE_ID")
        pay_id = data.get("PAY_ID")
        md = md5()
        s = "_".join((str(act), pay_account or "", serv_id or "", pay_id or "", self._lazy_object.secret))
        md.update(bytes(s, "utf-8"))
        our_sign = md.hexdigest()
        return our_sign == sign

    def get(self, request, *args, **kwargs):
        act: int = safe_int(request.GET.get("ACT"))
        self.current_date = timezone.now().strftime("%d.%m.%Y %H:%M")

        if not AllTimePayActEnum.in_range(act):
            return self._bad_ret(
                AllTimeStatusCodeEnum.BAD_REQUEST, "ACT has unexpected value"
            )

        try:
            sign = request.GET.get("SIGN")
            if not sign:
                return self._bad_ret(
                    AllTimeStatusCodeEnum.BAD_REQUEST, "SIGN not passed"
                )
            if not self.check_sign(request.GET, sign.lower()):
                return self._bad_ret(
                    AllTimeStatusCodeEnum.BAD_REQUEST, "Bad sign"
                )

            if act == AllTimePayActEnum.ACT_VIEW_INFO.value:
                return self._fetch_user_info(request.GET)
            elif act == AllTimePayActEnum.ACT_PAY_DO.value:
                return self._make_pay(request.GET)
            elif act == AllTimePayActEnum.ACT_PAY_CHECK.value:
                return self._check_pay(request.GET)
            else:
                return self._bad_ret(
                    AllTimeStatusCodeEnum.BAD_REQUEST, "ACT is not passed"
                )
        except Customer.DoesNotExist:
            return self._bad_ret(
                AllTimeStatusCodeEnum.CUSTOMER_NOT_FOUND, "Account does not exist"
            )
        except (PayAllTimeGateway.DoesNotExist, Http404):
            return self._bad_ret(
                AllTimeStatusCodeEnum.BAD_REQUEST, "Pay gateway does not exist"
            )
        except DatabaseError:
            return self._bad_ret(
                AllTimeStatusCodeEnum.SERVICE_UNAVIALABLE
            )
        except AllTimePayLog.DoesNotExist:
            return self._bad_ret(
                AllTimeStatusCodeEnum.TRANSACTION_NOT_FOUND
            )
        except AttributeError as err:
            return self._bad_ret(
                AllTimeStatusCodeEnum.BAD_REQUEST, str(err)
            )

    def _fetch_user_info(self, data: dict) -> Response:
        pay_account = data.get("PAY_ACCOUNT")
        customer = Customer.objects.get(username=pay_account, sites__in=[self.request.site], is_active=True)
        return Response(
            {
                "balance": round(customer.balance, 2),
                "name": customer.fio,
                "account": pay_account,
                "service_id": self._lazy_object.service_id,
                "min_amount": 10.0,
                "max_amount": 15000,
                "status_code": AllTimeStatusCodeEnum.PAYMENT_POSSIBLE.value,
                "time_stamp": self.current_date,
            }
        )

    def _make_pay(self, data: dict) -> Response:
        trade_point = data.get("TRADE_POINT", '')
        receipt_num = safe_int(data.get("RECEIPT_NUM"))
        pay_account = data.get("PAY_ACCOUNT")
        pay_id = data.get("PAY_ID")
        pay_amount = safe_float(data.get("PAY_AMOUNT"))
        customer = Customer.objects.filter(username=pay_account, is_active=True)
        if hasattr(self.request, 'site'):
            customer = customer.filter(sites__in=[self.request.site])
        customer = customer.get()
        pays = AllTimePayLog.objects.filter(pay_id=pay_id)
        if pays.exists():
            return self._bad_ret(
                AllTimeStatusCodeEnum.MORE_THAN_ONE_PAYMENTS, "Pay already exists"
            )

        with transaction.atomic():
            customer.add_balance(profile=None, cost=pay_amount, comment=f"{self._lazy_object.title} {pay_amount:.2f}")
            customer.save(update_fields=("balance",))

            AllTimePayLog.objects.create(
                customer=customer,
                pay_id=pay_id,
                sum=pay_amount,
                trade_point=trade_point,
                receipt_num=receipt_num,
                pay_gw=self._lazy_object,
            )
        customer_check_service_for_expiration(customer_id=customer.pk)
        return Response(
            {
                "pay_id": pay_id,
                "service_id": data.get("SERVICE_ID"),
                "amount": round(pay_amount, 2),
                "status_code": AllTimeStatusCodeEnum.PAYMENT_OK.value,
                "time_stamp": self.current_date,
            }
        )

    def _check_pay(self, data: dict) -> Response:
        pay_id = data.get("PAY_ID")
        pay = AllTimePayLog.objects.get(pay_id=pay_id)
        return Response(
            {
                "status_code": AllTimeStatusCodeEnum.TRANSACTION_STATUS_DETERMINED.value,
                "time_stamp": self.current_date,
                "transaction": {
                    "pay_id": pay_id,
                    "service_id": data.get("SERVICE_ID"),
                    "amount": round(pay.sum, 2),
                    "status": TRANSACTION_STATUS_PAYMENT_OK,
                    "time_stamp": pay.date_add.strftime("%d.%m.%Y %H:%M"),
                },
            }
        )
