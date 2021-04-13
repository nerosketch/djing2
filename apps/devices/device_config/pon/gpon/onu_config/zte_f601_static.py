import re
from typing import Optional

from devices.device_config import expect_util
from devices.device_config.pon.utils import get_all_vlans_from_config
from djing2.lib import process_lock, safe_int
from .zte_f601_bridge_config import ZteF601BridgeScriptModule, remove_from_olt
from ..zte_utils import zte_onu_conv_to_num, sn_to_mac, OnuZteRegisterError
from .zte_onu import onu_register_template


def get_onu_template(vlan_id: int):
    template = (
        "sn-bind enable sn",
        "tcont 1 profile HSI_100",
        "gemport 1 unicast tcont 1 dir both",
        "security storm-control broadcast rate 64 direction ingress vport 1",
        "security storm-control broadcast rate 64 direction egress vport 1",
        "switchport mode hybrid vport 1",
        "service-port 1 vport 1 user-vlan %(vid)d vlan %(vid)d" % {"vid": vlan_id},
        # "port-location format flexible-syntax vport 1",
        # "port-location sub-option remote-id enable vport 1",
        # "port-location sub-option remote-id name %s vport 1" % mac_addr,
        # "dhcp-option82 enable vport 1",
        # "dhcp-option82 trust true replace vport 1",
        "ip dhcp snooping enable vport 1",
        # 'ip-service ip-source-guard enable sport 1'
    )
    return template


def get_pon_mng_template(vlan_id: int):
    template = (
        "service HSI type internet gemport 1 vlan %d" % vlan_id,
        "loop-detect ethuni eth_0/1 enable",
        "vlan port eth_0/1 mode tag vlan %d" % vlan_id,
        "dhcp-ip ethuni eth_0/1 forbidden",
    )
    return template


def _register_f601_bridge_onu(
    ch, free_onu_number, serial, prompt, rack_num, fiber_num, user_vid, int_addr, *args, **kwargs
):
    onu_type = "ZTE-F601"
    serial = serial.upper()

    # register onu on olt interface
    ch.do_cmd("onu %d type %s sn %s" % (free_onu_number, onu_type, serial), "%s(config-if)#" % prompt)

    # Exit from int olt
    ch.do_cmd("exit", "%s(config)#" % prompt)

    # Enter to int onu
    ch.do_cmd(
        "int gpon-onu_%(int_addr)s:%(onu_num)d" % {"int_addr": int_addr, "onu_num": free_onu_number},
        "%s(config-if)#" % prompt,
    )

    # Apply int onu config
    template = get_onu_template(user_vid)
    for line in template:
        ch.do_cmd(line, "%s(config-if)#" % prompt)

    # Exit
    ch.do_cmd("exit", "%s(config)#" % prompt)

    # Enter to pon-onu-mng
    ch.do_cmd(
        "pon-onu-mng gpon-onu_%(int_addr)s:%(onu_num)d" % {"int_addr": int_addr, "onu_num": free_onu_number},
        "%s(gpon-onu-mng)#" % prompt,
    )

    # Apply config to pon-onu-mng
    for line in get_pon_mng_template(user_vid):
        ch.do_cmd(line, "%s(gpon-onu-mng)#" % prompt)

    # Exit
    ch.do_cmd("exit", "%s(config)#" % prompt)
    ch.do_cmd("exit", "%s#" % prompt)
    ch.sendline("exit")

    ch.close()
    return zte_onu_conv_to_num(rack_num=rack_num, fiber_num=fiber_num, port_num=free_onu_number)


# Main Entry point
@process_lock(lock_name="zte_olt")
def _register_onu(
    onu_mac: Optional[str],
    serial: str,
    zte_ip_addr: str,
    telnet_login: str,
    telnet_passw: str,
    telnet_prompt: str,
    config: dict,
    user_vid: int,
    *args,
    **kwargs,
):
    serial = serial.upper()

    if not re.match(r"^ZTEG[0-9A-F]{8}$", serial):
        raise expect_util.ExpectValidationError("Serial not valid, match: ^ZTEG[0-9A-F]{8}$")

    all_vids = get_all_vlans_from_config(config=config)
    if not all_vids:
        raise OnuZteRegisterError("not passed vlan list")

    onu_vlan = safe_int(all_vids[0])
    if onu_vlan == 0:
        raise OnuZteRegisterError("Bad vlan passed in config")

    if onu_mac is None:
        onu_mac = sn_to_mac(serial)

    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise expect_util.ExpectValidationError("ip address for zte not valid")

    return onu_register_template(
        register_fn=_register_f601_bridge_onu,
        hostname=zte_ip_addr,
        login=telnet_login,
        password=telnet_passw,
        prompt=telnet_prompt,
        user_vid=user_vid,
        serial=serial,
        onu_mac=onu_mac,
    )


remove_from_olt = remove_from_olt


class ZteF601StaticScriptModule(ZteF601BridgeScriptModule):
    title = "Zte F601 static"
    short_code = "zte_f601_static"
    reg_func = _register_onu
