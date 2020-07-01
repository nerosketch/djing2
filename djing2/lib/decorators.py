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
        api_auth_secret = getattr(settings, 'API_AUTH_SECRET')
        sign = request.GET.get('sign')
        if sign is None or sign == '':
            return HttpResponseForbidden('Access Denied')

        # Transmittent get list without sign
        get_values = request.GET.copy()
        del get_values['sign']
        values_list = [l for l in get_values.values() if l]
        values_list.sort()
        values_list.append(api_auth_secret)
        if check_sign(values_list, sign):
            return fn(request, *args, **kwargs)
        else:
            return HttpResponseForbidden('Access Denied')
    return wrapped
