from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.http.response import Http404
from . import main

handler_pairs = (
    (main.django_http_resp_404_handler, Http404),
    (main.django_validation_error_handler, ValidationError),
    (main.django_IntegrityError_handler, IntegrityError),
)

__all__ = ['handler_pairs']
