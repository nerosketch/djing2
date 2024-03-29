from hashlib import md5

from ._general import cached_property
from django.db import transaction, IntegrityError
from django.db.utils import DatabaseError
from django.http import Http404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from djing2.lib import IntEnumEx
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_xml.renderers import XMLRenderer
from djing2.lib import safe_int, safe_float
from djing2.viewsets import DjingModelViewSet
from fin_app.serializers import alltime as alltime_serializers
from fin_app.models.base_payment_model import fetch_customer_profile
from fin_app.models.alltime import AllTimePaymentLog, AllTimePayGateway

try:
    from customers.models import Customer
    from customers.tasks import customer_check_service_for_expiration_task
except ImportError as imperr:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        '"fin_app" application depends on "customers" '
        'application. Check if it installed'
    ) from imperr


class AllTimePayActEnum(IntEnumEx):
    ACT_VIEW_INFO = 1
    ACT_PAY_DO = 4
    ACT_PAY_CHECK = 7


class AllTimeStatusCodeEnum(IntEnumEx):
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
    queryset = AllTimePayGateway.objects.all()
    serializer_class = alltime_serializers.AllTimeGatewayModelSerializer

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )


class AllTimePayLogModelViewSet(DjingModelViewSet):
    queryset = AllTimePaymentLog.objects.all()
    serializer_class = alltime_serializers.AllTimePayLogModelSerializer


class AllTimeSpecifiedXMLRenderer(XMLRenderer):
    root_tag_name = "pay-response"


class AllTimePay(GenericAPIView):
    http_method_names = ["get"]
    renderer_classes = [AllTimeSpecifiedXMLRenderer]
    queryset = AllTimePayGateway.objects.all()
    serializer_class = alltime_serializers.PayAllTimeGatewayModelSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "pay_slug"
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]

    @cached_property
    def _lazy_object(self):
        return self.get_object()

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
        except (AllTimePayGateway.DoesNotExist, Http404):
            return self._bad_ret(
                AllTimeStatusCodeEnum.BAD_REQUEST, "Pay gateway does not exist"
            )
        except AllTimePaymentLog.DoesNotExist:
            return self._bad_ret(
                AllTimeStatusCodeEnum.TRANSACTION_NOT_FOUND
            )
        except IntegrityError:
            return self._bad_ret(
              AllTimeStatusCodeEnum.MORE_THAN_ONE_PAYMENTS, "Pay already exists"
            )
        except DatabaseError:
            return self._bad_ret(
                AllTimeStatusCodeEnum.SERVICE_UNAVIALABLE
            )
        except AttributeError as err:
            return self._bad_ret(
                AllTimeStatusCodeEnum.BAD_REQUEST, str(err)
            )

    def _fetch_user_info(self, data: dict) -> Response:
        pay_account = data.get("PAY_ACCOUNT")
        customer = fetch_customer_profile(self.request, username=pay_account)
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
        customer = fetch_customer_profile(self.request, username=pay_account)
        if pay_id is None:
            return self._bad_ret(
                AllTimeStatusCodeEnum.BAD_REQUEST, "Bad PAY_ID"
            )

        with transaction.atomic():
            customer.add_balance(
                profile=None,
                cost=pay_amount,
                comment=f"{self._lazy_object.title} {pay_amount:.2f}"
            )
            customer.save(update_fields=("balance",))

            AllTimePaymentLog.objects.create(
                customer=customer,
                pay_id=pay_id,
                amount=pay_amount,
                trade_point=trade_point,
                receipt_num=receipt_num,
                pay_gw=self._lazy_object,
            )
        customer_check_service_for_expiration_task.delay(customer_id=customer.pk)
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
        pay = AllTimePaymentLog.objects.get(pay_id=pay_id)
        return Response(
            {
                "status_code": AllTimeStatusCodeEnum.TRANSACTION_STATUS_DETERMINED.value,
                "time_stamp": self.current_date,
                "transaction": {
                    "pay_id": pay_id,
                    "service_id": data.get("SERVICE_ID"),
                    "amount": round(pay.amount, 2),
                    "status": TRANSACTION_STATUS_PAYMENT_OK,
                    "time_stamp": pay.date_add.strftime("%d.%m.%Y %H:%M"),
                },
            }
        )
