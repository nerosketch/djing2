import abc
from typing import Optional

from django.db.models import QuerySet, ManyToManyField
from django.db.utils import ProgrammingError
from django.http.request import split_domain_port, validate_host
from fastapi import Request, Depends, HTTPException
from starlette import status
from starlette.datastructures import Headers
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.models import Site


# TODO: May be move it to redis
SITE_CACHE = {}


def scheme(hdrs: Headers) -> str:
    if settings.SECURE_PROXY_SSL_HEADER:
        try:
            header, secure_value = settings.SECURE_PROXY_SSL_HEADER
        except ValueError:
            raise ImproperlyConfigured(
                'The SECURE_PROXY_SSL_HEADER setting must be a tuple containing two values.'
            )
        header_value = hdrs.get(header)
        if header_value is not None:
            return 'https' if header_value == secure_value else 'http'
    return 'http'


def is_secure() -> bool:
    return scheme == 'https'


def get_port(hdrs: Headers) -> str:
    """Return the port number for the request as a string."""
    if settings.USE_X_FORWARDED_PORT and 'HTTP_X_FORWARDED_PORT' in hdrs:
        port = hdrs['http_x_forwarded_port']
    else:
        port = hdrs['server_port']
    return str(port)


def get_raw_current_site_dependency(request: Request) -> str:
    hdrs = request.headers
    # raw_hdrs_list = request.headers.raw

    # We try three options, in order of decreasing preference.
    if settings.USE_X_FORWARDED_HOST and (
        'http_x_forwarded_host' in hdrs
    ):
        host = hdrs['http_x_forwarded_host']
    elif 'host' in hdrs:
        host = hdrs['host']
    else:
        # Reconstruct the host using the algorithm from PEP 333.
        host = hdrs['server_name']
        server_port = get_port(hdrs)
        if server_port != ('443' if is_secure() else '80'):
            host = '%s:%s' % (host, server_port)
    return host


def get_host_dependency(curr_raw_site_name: str = Depends(get_raw_current_site_dependency)) -> str:
    # Allow variants of localhost if ALLOWED_HOSTS is empty and DEBUG=True.
    allowed_hosts = settings.ALLOWED_HOSTS
    if settings.DEBUG and not allowed_hosts:
        allowed_hosts = ['.localhost', '127.0.0.1', '[::1]']

    domain, port = split_domain_port(curr_raw_site_name)
    if domain and validate_host(domain, allowed_hosts):
        return curr_raw_site_name
    else:
        msg = "Invalid HTTP_HOST header: %r." % curr_raw_site_name
        if domain:
            msg += " You may need to add %r to ALLOWED_HOSTS." % domain
        else:
            msg += " The domain name provided is not valid according to RFC 1034/1035."
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg
        )


def sites_dependency(host: str = Depends(get_host_dependency)) -> Site:
    try:
        # First attempt to look up the site by host with or without port.
        if host not in SITE_CACHE:
            SITE_CACHE[host] = Site.objects.get(domain__iexact=host)
        return SITE_CACHE[host]
    except Site.DoesNotExist:
        # Fallback to looking up site after stripping port from the host.
        domain, port = split_domain_port(host)
        if domain not in SITE_CACHE:
            SITE_CACHE[domain] = Site.objects.get(domain__iexact=domain)
        return SITE_CACHE[domain]


class FilterableBySitesModel(abc.ABC):
    sites = ManyToManyField(Site, blank=True)


def filter_qs_with_sites(qs: QuerySet[FilterableBySitesModel], curr_site: Optional[Site], curr_user):
    rqs = qs
    if curr_user.is_superuser:
        return rqs
    if curr_site:
        model = qs
        if hasattr(model, 'sites'):
            rqs = qs.filter(sites__in=[curr_site])
        elif hasattr(model, 'site'):
            rqs = qs.filter(site=curr_site)
        else:
            raise ProgrammingError('Model "%s" has no field "sites" nor "site"' % model)
    return rqs
