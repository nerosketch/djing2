from .zte_f601_bridge_config import ZteF601BridgeScriptModule


def _get_onu_template(user_vid: int, onu_mac: str, *args, **kwargs) -> tuple:
    return (
        "switchport mode hybrid vport 1",
        "service-port 1 vport 1 user-vlan %d vlan %d" % (user_vid, user_vid),
        "port-location format flexible-syntax vport 1",
        "port-location sub-option remote-id enable vport 1",
        "port-location sub-option remote-id name %s vport 1" % onu_mac,
        "dhcp-option82 enable vport 1",
        "dhcp-option82 trust true replace vport 1",
        "ip dhcp snooping enable vport 1",
        "ip-service ip-source-guard enable sport 1",
    )


class FD511GOnuDeviceConfigType(ZteF601BridgeScriptModule):
    title = "FD511G IPOE Bridge"
    short_code = "fd511g_ipoe_bridge"
    sn_regexp = r"^HWTC[0-9A-F]{8}$"
    accept_vlan = False
    zte_type = 'FD511G'

    @staticmethod
    def format_sn_from_mac(mac: str) -> str:
        # Format serial number from mac address
        # because saved mac address got from serial number
        sn = "HWTC%s" % "".join("%.2X" % int(x, base=16) for x in mac.split(":")[-4:])
        return sn

    def apply_zte_top_conf(self, *args, **kwargs) -> None:
        return super().apply_zte_top_conf(get_onu_template_fn=_get_onu_template, *args, **kwargs)

    def apply_zte_bot_conf(self, *args, **kwargs):
        pass

    def register_onu_on_olt_interface(
        self, free_onu_number: int, serial: str, prompt: str, onu_type: str, int_addr: str
    ) -> None:
        # go to olt interface
        self.ch.do_cmd("interface gpon-olt_%s" % int_addr, "%s(config-if)#" % prompt)

        # register onu on olt interface
        self.ch.do_cmd(f"onu {free_onu_number} type {onu_type} sn {serial}", prompt)

        # register onu profile on olt interface
        self.ch.do_cmd(f"onu {free_onu_number} profile line {onu_type}-LINE remote FD511G_BR", prompt)

        # Exit from int olt
        self.ch.do_cmd("exit", "%s(config)#" % prompt)
