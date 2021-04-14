import re

from devices.device_config import expect_util
from devices.device_config.pon.gpon import zte_utils
from djing2.lib import process_lock
from .zte_f601_bridge_config import ZteF601BridgeScriptModule
from .zte_onu import onu_register_template


def _get_onu_template(vlan_id: int, mac_addr: str) -> tuple:
    return (
        "switchport mode hybrid vport 1",
        "service-port 1 vport 1 user-vlan %d vlan %d" % (vlan_id, vlan_id),
        "port-location format flexible-syntax vport 1",
        "port-location sub-option remote-id enable vport 1",
        "port-location sub-option remote-id name %s vport 1" % mac_addr,
        "dhcp-option82 enable vport 1",
        "dhcp-option82 trust true replace vport 1",
        "ip dhcp snooping enable vport 1",
        "ip-service ip-source-guard enable sport 1",
    )


def _register_onu(ch, free_onu_number, serial, prompt, rack_num, fiber_num, user_vid, onu_mac, *args, **kwargs):
    # register onu on olt interface
    ch.do_cmd(f"onu {free_onu_number} type ZTE-F660 sn {serial}", prompt)
    # register onu profile on olt interface
    ch.do_cmd(f"onu {free_onu_number} profile line ZTE-F660-LINE remote ZTE-F660-ROUTER", prompt)

    # Exit from int olt
    ch.do_cmd("exit", f"{prompt}(config)#")

    # Enter to int onu
    ch.do_cmd(f"int gpon-onu_1/{rack_num}/{fiber_num}:{free_onu_number}", prompt)

    # Apply int onu config
    template = _get_onu_template(vlan_id=user_vid, mac_addr=onu_mac)
    for line in template:
        ch.do_cmd(line, prompt)

    # Exit
    ch.do_cmd("exit", f"{prompt}(config)#")
    ch.do_cmd("exit", f"{prompt}#")
    ch.sendline("exit")
    ch.close()
    return zte_utils.zte_onu_conv_to_num(rack_num=rack_num, fiber_num=fiber_num, port_num=free_onu_number)


# apply vlan config
@process_lock(lock_name="zte_olt")
def _zte_onu_router_config_apply(
    serial: str,
    onu_mac: str,
    zte_ip_addr: str,
    telnet_login: str,
    telnet_passw: str,
    telnet_prompt: str,
    user_vid: int,
    *args,
    **kwargs,
):
    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise expect_util.ExpectValidationError("ip address for zte not valid")

    return onu_register_template(
        register_fn=_register_onu,
        hostname=zte_ip_addr,
        login=telnet_login,
        password=telnet_passw,
        prompt=telnet_prompt,
        user_vid=user_vid,
        serial=serial,
        onu_mac=onu_mac,
    )


class ZteF660RouterScriptModule(ZteF601BridgeScriptModule):
    title = "Zte ONU F660 Router"
    short_code = "zte_f660_router"
    accept_vlan = False
    reg_func = _zte_onu_router_config_apply
