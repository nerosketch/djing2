from functools import wraps
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.http import Http404
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import status
from djing2.viewsets import DjingModelViewSet
from djing2.lib.mixins import SitesFilterMixin
from ._general import cached_property
from fin_app.models.base_payment_model import fetch_customer_profile, Customer
from fin_app.models import payme as pmodels
from fin_app.serializers import payme as payme_serializers


def _payment_method_wrapper(request_serializer):
    def _fn(fn):
        @wraps(fn)
        def _wrapper(self, data, *args, **kwargs):
            ser = request_serializer(data=data)
            ser.is_valid(raise_exception=True)
            res = fn(self, data=ser.validated_data, *args, **kwargs)
            return res

        return _wrapper
    return _fn


_paymeAnonUser = AnonymousUser()

class PaymeBasicAuthentication(BaseAuthentication):
    """
    Simple base64 authentication.

    Pay system should authenticate by passing the base64(login:password) key in the "Authorization"
    HTTP header, prepended with the string "Basic ".  For example:

        Authorization: Basic TG9naW46UGFzcw==
    """

    keyword = 'Basic'
    model = None

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode() or len(auth) == 1:
            msg = _('Invalid login header. No credentials provided.')
            raise pmodels.PaymeAuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid login header. Credentials string should not contain spaces.')
            raise pmodels.PaymeAuthenticationFailed(msg)

        try:
            credentials_base64 = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid credentials header. Credentials string should not contain invalid characters.')
            raise pmodels.PaymeAuthenticationFailed(msg)

        return self.authenticate_credentials(credentials_base64)

    def authenticate_credentials(self, key):
        payme_credentials = getattr(settings, 'PAYME_CREDENTIALS')
        if not payme_credentials:
            raise pmodels.PaymeAuthenticationFailed('PAYME_CREDENTIALS is not specified in settings')

        if payme_credentials != key:
            raise pmodels.PaymeAuthenticationFailed(_('Invalid username/password.'))

        return (_paymeAnonUser, None)

    def authenticate_header(self, request):
        return self.keyword


class PaymePaymentEndpoint(SitesFilterMixin, GenericAPIView):
    http_method_names = ['post']
    permission_classes = [AllowAny]
    authentication_classes = [PaymeBasicAuthentication]
    serializer_class = payme_serializers.PaymePaymentGatewayModelSerializer
    queryset = pmodels.PaymePaymentGatewayModel.objects.all()
    lookup_field = "slug"
    lookup_url_kwarg = "pay_slug"

    @cached_property
    def _lazy_object(self):
        try:
            return self.get_object()
        except Http404:
            raise pmodels.PaymeCustomerNotFound

    def filter_queryset(self, queryset):
        return queryset

    def http_method_not_allowed(self, request, *args, **kwargs):
        return Response({
            'error': {
                'code': pmodels.PaymeErrorsEnum.METHOD_IS_NO_POST.value,
                'message': pmodels.ugettext_lazy('HTTP Method is not allowed'),
                'data': pmodels.PaymeBaseRPCException.get_data()
            },
        }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            rpc_method_name = data.get('method')
            if rpc_method_name not in pmodels.PaymeRPCMethodNames.values:
                raise pmodels.PaymeRpcMethodError
            rpc_method = self.rpc_methods.get(rpc_method_name, self._no_method_found)
            r = rpc_method(self, data)
            r.update({
                'id': data.get('id')
            })
            return Response(r, status=status.HTTP_200_OK)
        except pmodels.PaymeBaseRPCException as err:
            err_dict = {
                'code': err.get_code().value,
                'message': err.get_msg(),
                'data': err.get_data()
            }
            return Response({
                'error': err_dict,
                'id': data.get('id')
            }, status=status.HTTP_200_OK)
        except Customer.DoesNotExist:
            return Response({
                'error': {
                    'code': pmodels.PaymeCustomerNotFound.code.value,
                    'message': pmodels.PaymeCustomerNotFound.msg,
                    'data': pmodels.PaymeBaseRPCException.get_data()
                },
                'id': data.get('id')
            })
        except ValidationError:
            return Response({
                'error': {
                    'code': pmodels.PaymeErrorsEnum.JSON_PARSE_ERROR.value,
                    'message': pmodels.ugettext_lazy('Data validation error'),
                    'data': pmodels.PaymeBaseRPCException.get_data()
                },
                'id': data.get('id')
            }, status=status.HTTP_200_OK)

    def _no_method_found(self, _):
        raise pmodels.PaymeRpcMethodError

    @_payment_method_wrapper(
        payme_serializers.PaymeCheckPerformTransactionRequestSerializer
    )
    def check_perform_transaction(self, data) -> dict:
        params = data['params']
        uname = params['account']['username']
        self._lazy_object
        fetch_customer_profile(self.request, username=uname)
        return {
            "result": {"allow": True}
        }

    @_payment_method_wrapper(
        payme_serializers.PaymeCreateTransactionRequestSerializer
    )
    def create_transaction(self, data) -> dict:
        params = data['params']
        uname = params['account']['username']
        customer = fetch_customer_profile(self.request, username=uname)
        transaction = pmodels.PaymeTransactionModel.objects.start_transaction(
            external_id=params['id'],
            customer=customer,
            external_time=params['time'],
            amount=params['amount']
        )
        return transaction.as_dict()

    @_payment_method_wrapper(
        payme_serializers.PaymePerformTransactionRequestSerializer
    )
    def perform_transaction(self, data) -> dict:
        params = data['params']
        trans_id = params['id']
        return pmodels.PaymeTransactionModel.objects.provide_payment(
            transaction_id=trans_id,
            gw=self._lazy_object
        )

    @_payment_method_wrapper(
        payme_serializers.PaymeCancelTransactionRequestSerializer
    )
    def cancel_transaction(self, data) -> dict:
        params = data['params']
        trans_id = params['id']
        return pmodels.PaymeTransactionModel.objects.cancel_transaction(
            transaction_id=trans_id,
        )

    @_payment_method_wrapper(
        payme_serializers.PaymeCheckTransactionRequestSerializer
    )
    def check_transaction(self, data) -> dict:
        params = data['params']
        trans_id = params['id']
        return pmodels.PaymeTransactionModel.objects.check_payment(
            transaction_id=trans_id,
        )

    @_payment_method_wrapper(
        payme_serializers.PaymeGetStatementMethodRequestSerializer
    )
    def get_statement(self, data) -> dict:
        params = data['params']
        from_time = params['from']
        to_time = params['to']
        statement_queryset = pmodels.PaymeTransactionModel.objects.filter(
            external_time__gte=from_time, external_time__lte=to_time
        )
        statement_serializer = payme_serializers.PaymeTransactionStatementSerializer(
            statement_queryset, many=True
        )
        return {'result': {
            'transactions': statement_serializer.data
        }}

    rpc_methods = {
        pmodels.PaymeRPCMethodNames.CHECK_PERFORM_TRANSACTION.value: check_perform_transaction,
        pmodels.PaymeRPCMethodNames.CREATE_TRANSACTION.value: create_transaction,
        pmodels.PaymeRPCMethodNames.PERFORM_TRANSACTION.value: perform_transaction,
        pmodels.PaymeRPCMethodNames.CANCEL_TRANSACTION.value: cancel_transaction,
        pmodels.PaymeRPCMethodNames.CHECK_TRANSACTION.value: check_transaction,
        pmodels.PaymeRPCMethodNames.GET_STATEMENT.value: get_statement,
    }


class PaymeLogModelViewSet(DjingModelViewSet):
    queryset = pmodels.PaymePaymentLogModel.objects.all()
    serializer_class = payme_serializers.PaymePaymentLogModelSerializer


class PaymePaymentGatewayModelViewSet(DjingModelViewSet):
    queryset = pmodels.PaymePaymentGatewayModel.objects.all()
    serializer_class = payme_serializers.PaymePaymentGatewayModelSerializer

