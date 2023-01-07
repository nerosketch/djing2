import re
import os
from django.conf import settings
from .celery import app as celery_app
from djing2.email_backend import send_smtp_email_task  # noqa


IP_ADDR_REGEX = (
    r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

MAC_ADDR_REGEXP = r"^([0-9a-fA-F]{2}[:.-]){5}[0-9a-fA-F]{2}|([0-9a-fA-F]{4}[:.-]){2}[0-9a-fA-F]{4}$"


def ping(ip_addr: str, count=1, interval=0.2) -> bool:
    if re.match(IP_ADDR_REGEX, ip_addr):
        response = os.system(f"`which ping` -4Anq -i {interval} -c{count} -W1 {ip_addr} > /dev/null")
        return response == 0
    else:
        raise ValueError('"ip_addr" is not valid ip address')


__all__ = ("ping", "MAC_ADDR_REGEXP", "IP_ADDR_REGEX", "celery_app",
           "send_smtp_email_task")
