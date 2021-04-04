import re
import os
from django.conf import settings

MAC_ADDR_REGEX = "^([0-9A-Fa-f]{1,2}[:-]){5}([0-9A-Fa-f]{1,2})$"

IP_ADDR_REGEX = (
    r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
    "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def ping(ip_addr: str, count=1, arp=False, interval=0.2) -> bool:
    if re.match(IP_ADDR_REGEX, ip_addr):
        if arp:
            arping_command = getattr(settings, "ARPING_COMMAND", "arping")
            response = os.system(f"{arping_command} -qc{count} -W {interval} {ip_addr} > /dev/null")
        else:
            response = os.system(f"`which ping` -4Anq -i {interval} -c{count} -W1 {ip_addr} > /dev/null")
        return response == 0
    else:
        raise ValueError('"ip_addr" is not valid ip address')


__all__ = ("ping", "MAC_ADDR_REGEX", "IP_ADDR_REGEX")
