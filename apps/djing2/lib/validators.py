from django.core.validators import RegexValidator
from django.conf import settings

tel_regexp_str = getattr(settings, "TELEPHONE_REGEXP", r"^(\+[7893]\d{10,11})?$")

latinValidator = RegexValidator(r"^\w{1,127}$")
telephoneValidator = RegexValidator(tel_regexp_str)
