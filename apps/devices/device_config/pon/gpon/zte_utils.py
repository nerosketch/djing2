import re

from django.utils.translation import gettext
from devices.device_config.base import DeviceConsoleError


class ZteOltConsoleError(DeviceConsoleError):
    def __init__(self, message=None):
        self.message = message or "ZTE OLT Console error"


class OnuZteRegisterError(ZteOltConsoleError):
    pass


class ZTEFiberIsFull(ZteOltConsoleError):
    def __init__(self, message=None):
        self.message = message or "ZTE OLT fiber is full"


class ZteOltLoginFailed(ZteOltConsoleError):
    def __init__(self, message=None):
        self.message = message or gettext("Wrong login or password for telnet access")


def parse_onu_name(onu_name: str, name_regexp=re.compile("[/:_]")):
    gpon_onu, stack_num, rack_num, fiber_num, onu_num = name_regexp.split(onu_name)
    return {"stack_num": stack_num, "rack_num": rack_num, "fiber_num": fiber_num, "onu_num": onu_num}


def get_unregistered_onu(lines, serial):
    for line in lines:
        if line.startswith("gpon-onu_"):
            spls = re.split(r"\s+", line)
            if len(spls) > 2:
                if serial == spls[1]:
                    onu_index, sn, state = spls[:3]
                    return parse_onu_name(onu_index)


def get_free_registered_onu_number(lines):
    onu_type_regexp = re.compile(r"^\s{1,5}onu \d{1,3} type [-\w\d]{4,64} sn \w{4,64}$")
    onu_olt_num = None
    i = 0
    for line in lines:
        if onu_type_regexp.match(line):
            # match line
            i += 1
            onu, num, onu_type, onu_type, sn, onu_sn = line.split()
            onu_olt_num = int(num)
            if onu_olt_num > i:
                return i
    if onu_olt_num is None:
        return 1
    return onu_olt_num + 1


def sn_to_mac(sn: str):
    if not sn:
        return
    t = sn[4:].lower()
    r = tuple(t[i : i + 2] for i in range(0, len(t), 2))
    return "45:47:%s" % ":".join(r)


def zte_onu_conv_to_num(rack_num: int, fiber_num: int, port_num: int):
    r = f"10000{rack_num:08b}{fiber_num:08b}00000000"
    snmp_fiber_num = int(r, base=2)
    return "%d.%d" % (snmp_fiber_num, port_num)


def zte_onu_conv_from_onu(snmp_info: str) -> tuple:
    try:
        fiber_num, onu_num = (int(i) for i in snmp_info.split("."))
        fiber_num_bin = bin(fiber_num)[2:]
        rack_num = int(fiber_num_bin[5:13], base=2)
        fiber_num = int(fiber_num_bin[13:21], base=2)
        return rack_num, fiber_num, onu_num
    except ValueError:
        raise OnuZteRegisterError("Bad snmp info format for zte")


def conv_zte_signal(lvl: int) -> float:
    if lvl == 65535:
        return 0.0
    r = 0
    if 0 < lvl < 30000:
        r = lvl * 0.002 - 30
    elif 60000 < lvl < 65534:
        r = (lvl - 65534) * 0.002 - 30
    return round(r, 2)
