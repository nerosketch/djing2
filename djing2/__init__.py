import re
import os


IP_ADDR_REGEX = (
    '^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
    '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)


def ping(ip_addr: str, count=1):
    if re.match(IP_ADDR_REGEX, ip_addr):
        response = os.system("`which ping` -4Anq -c%d -W1 %s > /dev/null" % (count, ip_addr))
        return True if response == 0 else False
    else:
        return False
