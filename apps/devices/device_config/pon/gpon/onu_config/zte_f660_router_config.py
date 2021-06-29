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


class ZteF660RouterScriptModule(ZteF601BridgeScriptModule):
    title = "Zte ONU F660 Router"
    short_code = "zte_f660_router"
    accept_vlan = False
    zte_type = "ZTE-F660"

    def apply_zte_bot_conf(self, *args, **kwargs) -> None:
        pass

    def apply_zte_top_conf(self, *args, **kwargs) -> None:
        return super().apply_zte_top_conf(get_onu_template_fn=_get_onu_template, *args, **kwargs)

    def register_onu_on_olt_interface(
        self, free_onu_number: int, serial: str, prompt: str, onu_type: str, int_addr: str
    ) -> None:
        # go to olt interface
        self.ch.do_cmd("interface gpon-olt_%s" % int_addr, "%s(config-if)#" % prompt)

        # register onu on olt interface
        self.ch.do_cmd(f"onu {free_onu_number} type {onu_type} sn {serial}", prompt)
        # register onu profile on olt interface
        self.ch.do_cmd(f"onu {free_onu_number} profile line {onu_type}-LINE remote {onu_type}-ROUTER", prompt)

        # Exit from int olt
        self.ch.do_cmd("exit", "%s(config)#" % prompt)
