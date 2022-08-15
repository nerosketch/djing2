import sys


if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from django.utils.functional import cached_property

