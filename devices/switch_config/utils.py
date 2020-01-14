import re
from typing import AnyStr, Optional
from transliterate import translit


def norm_name(name: str, replreg=None):
    if replreg is None:
        return re.sub(pattern='\W{1,255}', repl='', string=name, flags=re.IGNORECASE)
    return replreg.sub('', name)


def plain_ip_device_mon_template(device) -> Optional[AnyStr]:
    if not device:
        raise ValueError

    parent_host_name = norm_name("%d%s" % (
        device.parent_dev.pk, translit(device.parent_dev.comment, language_code='ru', reversed=True)
    )) if device.parent_dev else None

    host_name = norm_name("%d%s" % (device.pk, translit(device.comment, language_code='ru', reversed=True)))
    mac_addr = device.mac_addr
    r = (
        "define host{",
        "\tuse				generic-switch",
        "\thost_name		%s" % host_name,
        "\taddress			%s" % device.ip_address,
        "\tparents			%s" % parent_host_name if parent_host_name is not None else '',
        "\t_mac_addr		%s" % mac_addr if mac_addr is not None else '',
        "}\n"
    )
    return '\n'.join(i for i in r if i)


def macbin2str(bin_mac: bytes) -> str:
    return ':'.join('%x' % ord(i) for i in bin_mac) if bin_mac else None
