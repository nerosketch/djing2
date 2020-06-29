import re
import os
from uwsgi_tasks import set_uwsgi_callbacks

MAC_ADDR_REGEX = '^([0-9A-Fa-f]{1,2}[:-]){5}([0-9A-Fa-f]{1,2})$'

IP_ADDR_REGEX = (
    '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)


def ping(ip_addr: str, count=1) -> bool:
    if re.match(IP_ADDR_REGEX, ip_addr):
        response = os.system("`which ping` -4Anq -i 0.2 -c%d -W1 %s > /dev/null" % (count, ip_addr))
        return response == 0
    else:
        return False


__all__ = ('ping', 'MAC_ADDR_REGEX', 'IP_ADDR_REGEX')

set_uwsgi_callbacks()
