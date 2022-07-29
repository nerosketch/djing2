from functools import wraps
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework import status
from fin_app.models.base_payment_model import fetch_customer_profile
from fin_app.models.payme import (
    PaymeRPCMethodNames, PaymeRpcMethodError,
    PeymeBaseRPCException, PaymeErrorsEnum
)


def _rpc_request_wrapper(fn):
    @wraps(fn)
    def _wrapped(self, request, *args, **kwargs):
        try:
            r = fn(request, *args, **kwargs)
            return Response(r, status=status.HTTP_200_OK)
        except PeymeBaseRPCException as err:
            err_dict = {
                'code': err.get_code().value,
                'message': err.get_msg()
            }
            err_data = err.get_data()
            if err_data is not None and isinstance(err_data, dict):
                err_dict.update({
                    'data': err_data
                })
            return Response({
                'error': err_dict,
                'id': request.data.get('id')
            }, status=status.HTTP_200_OK)
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

    return _wrapped


class PaymePaymentEndpoint(GenericAPIView):
    http_method_names = ['post']
    permission_classes = [AllowAny]
    #  serializer_class =

    @_rpc_request_wrapper
    def post(self, request, *args, **kwargs):
        dat = request.data
        rpc_method_name = dat.get('method')
        if rpc_method_name not in PaymeRPCMethodNames.values:
            raise PaymeRpcMethodError
        rpc_method = self.rpc_methods.get(rpc_method_name, self._no_method_found)
        return rpc_method(self, request)

    def _no_method_found(self, _):
        raise PaymeRpcMethodError

    def check_perform_transaction(self, request) -> dict:
        # TODO: ...
        customer = fetch_customer_profile(self.request, username=pay_account)
        pass

    def create_transaction(self, request) -> dict:
        # TODO: ...
        pass

    def perform_transaction(self, request) -> dict:
        # TODO: ...
        pass

    def cancel_transaction(self, request) -> dict:
        # TODO: ...
        pass

    def check_transaction(self, request) -> dict:
        # TODO: ...
        pass

    def get_statement(self, request) -> dict:
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
