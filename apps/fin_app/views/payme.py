from functools import wraps
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from djing2.viewsets import DjingModelViewSet
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
            res = fn(self, data=ser.data, *args, **kwargs)
            return res

        return _wrapper
    return _fn


class PaymePaymentEndpoint(GenericAPIView):
    http_method_names = ['post']
    permission_classes = [AllowAny]
    #  serializer_class =
    #  queryset = pmodels.PaymePaymentGatewayModel.objects.all()
    lookup_field = "slug"
    lookup_url_kwarg = "pay_slug"

    @cached_property
    def _lazy_object(self):
        return self.get_object()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(sites__in=[self.request.site])

    def http_method_not_allowed(self, request, *args, **kwargs):
        return Response({
            'error': {
                'code': pmodels.PaymeErrorsEnum.METHOD_IS_NO_POST.value,
                'message': {
                    'ru': 'HTTP Метод не допустим',
                    'en': 'HTTP Method is not allowed'
                },
                'data': 'username'
            },
        }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            rpc_method_name = data.get('method')
            if rpc_method_name not in pmodels.PaymeRPCMethodNames.values:
                raise pmodels.PaymeRpcMethodError
            rpc_method = self.rpc_methods.get(rpc_method_name, self._no_method_found)
            r = rpc_method(self, data)
            return Response(r, status=status.HTTP_200_OK)
        except pmodels.PaymeBaseRPCException as err:
            err_dict = {
                'code': err.get_code().value,
                'message': err.get_msg(),
                'data': 'username'
            }
            err_data = err.get_data()
            if err_data is not None and isinstance(err_data, dict):
                err_dict.update({
                    'data': {
                        'account': err_data
                    }
                })
            return Response({
                'error': err_dict,
                'id': request.data.get('id')
            }, status=status.HTTP_200_OK)
        except Customer.DoesNotExist:
            return Response({
                'error': {
                    'code': pmodels.PaymeCustomerNotFound.code.value,
                    'message': pmodels.PaymeCustomerNotFound.msg,
                    'data': 'username'
                },
                'id': request.data.get('id')
            })
        except ValidationError:
            return Response({
                'error': {
                    'code': pmodels.PaymeErrorsEnum.JSON_PARSE_ERROR.value,
                    'message': {
                        'ru': 'Ошибка валидации данных',
                        'en': 'Data validation error'
                    },
                    'data': 'username'
                },
            }, status=status.HTTP_200_OK)

    def _no_method_found(self, _):
        raise pmodels.PaymeRpcMethodError

    @_payment_method_wrapper(
        payme_serializers.PaymeCheckPerformTransactionRequestSerializer
    )
    def check_perform_transaction(self, data) -> dict:
        params = data['params']
        uname = params['account']['username']
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
        return {'result': {
            'create_time': int(transaction.date_add.timestamp() * 1000),
            'transaction': transaction.pk,
            'state': transaction.transaction_state.value
        }}

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
        from_time = data['from_time']
        to_time = data['to_time']
        statement_queryset = pmodels.PaymeTransactionModel.objects.filter(
            external_time__lte=from_time, external_time__gte=to_time
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

