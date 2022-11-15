from django.http.response import Http404
from .main import django_http_resp_404_handler

handler_pairs = (
    (django_http_resp_404_handler, Http404),
)

__all__ = ['handler_pairs']
