from functools import wraps
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework import status
from fin_app.models.base_payment_model import fetch_customer_profile, Customer
from fin_app.models.payme import (
    PaymeRPCMethodNames, PaymeRpcMethodError,
    PeymeBaseRPCException, PaymeErrorsEnum
)
from fin_app.serializers import payme as payme_serializers


def _payment_method_wrapper(request_serializer):
    def _fn(fn):
        @wraps(fn)
        def _wrapper(self, data, *args, **kwargs):
            ser = request_serializer(data=data)
            ser.is_valid(raise_exception=True)
            res = fn(self, data=ser.data, *args, **kwargs)
            return Response(res)

        return _wrapper
    return _fn


class PaymePaymentEndpoint(GenericAPIView):
    http_method_names = ['post']
    permission_classes = [AllowAny]
    #  serializer_class =

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            rpc_method_name = data.get('method')
            if rpc_method_name not in PaymeRPCMethodNames.values:
                raise PaymeRpcMethodError
            rpc_method = self.rpc_methods.get(rpc_method_name, self._no_method_found)
            r = rpc_method(self, data)
            return Response(r, status=status.HTTP_200_OK)
        except PeymeBaseRPCException as err:
            err_dict = {
                'code': err.get_code().value,
                'message': err.get_msg()
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
        except Customer.DoesNotExists:
            return Response({
                'error': {
                    'code': PaymeErrorsEnum.CUSTOMER_DOES_NOT_EXISTS.value,
                    'message': {
                        'ru': 'Абонент не найден',
                        'en': 'Customer does not exists'
                    }
                },
                'id': request.data.get('id')
            })
        except MethodNotAllowed:
            return Response({
                'error': {
                    'code': PaymeErrorsEnum.METHOD_IS_NO_POST.value,
                    'message': {
                        'ru': 'HTTP Метод не допустим',
                        'en': 'HTTP Method is not allowed'
                    }
                },
                'id': request.data.get('id')
            }, status=status.HTTP_200_OK)

    def _no_method_found(self, _):
        raise PaymeRpcMethodError

    @_payment_method_wrapper(
        payme_serializers.PaymeCheckPerformTransactionRequestSerializer
    )
    def check_perform_transaction(self, data) -> dict:
        # TODO: ...
        params = data['params']
        uname = params['account']['username']
        customer = fetch_customer_profile(self.request, username=uname)
        return {
            "result": {"allow": True}
        }


    @_payment_method_wrapper(
        payme_serializers.
    )
    def create_transaction(self, data) -> dict:
        # TODO: ...
        pass

    @_payment_method_wrapper(
        payme_serializers.
    )
    def perform_transaction(self, data) -> dict:
        # TODO: ...
        pass

    @_payment_method_wrapper(
        payme_serializers.
    )
    def cancel_transaction(self, data) -> dict:
        # TODO: ...
        pass

    @_payment_method_wrapper(
        payme_serializers.
    )
    def check_transaction(self, data) -> dict:
        # TODO: ...
        pass

    @_payment_method_wrapper(
        payme_serializers.
    )
    def get_statement(self, data) -> dict:
        # TODO: ...
        pass

    rpc_methods = {
        # TODO: ...
        PaymeRPCMethodNames.CHECK_PERFORM_TRANSACTION.value: check_perform_transaction,
        PaymeRPCMethodNames.CREATE_TRANSACTION.value: create_transaction,
        PaymeRPCMethodNames.PERFORM_TRANSACTION.value: perform_transaction,
        PaymeRPCMethodNames.CANCEL_TRANSACTION.value: cancel_transaction,
        PaymeRPCMethodNames.CHECK_TRANSACTION.value: check_transaction,
        PaymeRPCMethodNames.GET_STATEMENT.value: get_statement,
    }
