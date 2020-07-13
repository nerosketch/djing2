from functools import wraps
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from djing2.lib import check_sign


# Allow to view only admins
def only_admins(fn):
    @wraps(fn)
    def wrapped(request, *args, **kwargs):
        if request.user.is_admin:
            return fn(request, *args, **kwargs)
        else:
            return redirect('client_side:home')
    return wrapped


# hash auth for functional views
def hash_auth_view(fn):
    @wraps(fn)
    def wrapped(request, *args, **kwargs):
        sign = request.headers.get('Api-Auth-Sign')
        if getattr(settings, 'DEBUG', False) or sign is None:
            sign = request.META.get('Api-Auth-Sign')
        if not sign:
            return HttpResponseForbidden('Access Denied!')
        get_values = request.GET.copy()
        if check_sign(get_values, sign):
            return fn(request, *args, **kwargs)
        else:
            return HttpResponseForbidden('Access Denied')
    return wrapped
