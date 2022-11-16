from django.http.response import Http404
from .main import django_http_resp_404_handler, catch_logic_error
from djing2.lib import LogicError

handler_pairs = (
    (django_http_resp_404_handler, Http404),
    (catch_logic_error, LogicError),
)

__all__ = ['handler_pairs']
