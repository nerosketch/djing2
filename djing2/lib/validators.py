from django.core.validators import RegexValidator
from django.conf import settings


latinValidator = RegexValidator(r'^\w{1,127}$')
telephoneValidator = RegexValidator(
    getattr(settings, 'TELEPHONE_REGEXP', r'^(\+[7893]\d{10,11})?$')
)
