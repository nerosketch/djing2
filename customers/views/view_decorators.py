from rest_framework import status
from rest_framework.response import Response

from djing2.lib import LogicError
# from gateways.nas_managers import GatewayFailedResult, GatewayNetworkError


def catch_customers_errs(fn):
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except LogicError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        except TimeoutError as e:
            return Response(str(e), status=status.HTTP_408_REQUEST_TIMEOUT)

    # Hack for decorator @action
    wrapper.__name__ = fn.__name__
    return wrapper
