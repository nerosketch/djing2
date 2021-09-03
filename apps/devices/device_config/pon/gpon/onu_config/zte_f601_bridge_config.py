from .zte_onu import ZteOnuDeviceConfigType


def get_onu_template(user_vid: int, onu_mac: str, *args, **kwargs) -> tuple:
    template = (
        "sn-bind enable sn",
        "tcont 1 profile HSI_100",
        "gemport 1 unicast tcont 1 dir both",
        "security storm-control broadcast rate 8 direction ingress vport 1",
        "security storm-control broadcast rate 8 direction egress vport 1",
        "switchport mode hybrid vport 1",
        "service-port 1 vport 1 user-vlan %d vlan %d" % (user_vid, user_vid),
        "port-location format flexible-syntax vport 1",
        "port-location sub-option remote-id enable vport 1",
        "port-location sub-option remote-id name %s vport 1" % onu_mac,
        "dhcp-option82 enable vport 1",
        "dhcp-option82 trust true replace vport 1",
        "ip dhcp snooping enable vport 1",
        # 'ip-service ip-source-guard enable sport 1'
    )
    return template


def get_pon_mng_template(user_vid: int, *args, **kwargs) -> tuple:
    template = (
        "service HSI type internet gemport 1 vlan %d" % user_vid,
        "loop-detect ethuni eth_0/1 enable",
        "vlan port eth_0/1 mode tag vlan %d" % user_vid,
        "dhcp-ip ethuni eth_0/1 from-internet",
    )
    return template


class ZteF601BridgeScriptModule(ZteOnuDeviceConfigType):
    title = "Zte F601 dhcp"
    short_code = "zte_f601_bridge"
    accept_vlan = True
    zte_type = "ZTE-F601"

    def apply_zte_top_conf(
        self, prompt: str, free_onu_number: int, int_addr: str, get_onu_template_fn=get_onu_template, *args, **kwargs
    ) -> None:
        # Enter to int onu
        self.ch.do_cmd(
            "int gpon-onu_%(int_addr)s:%(onu_num)d" % {"int_addr": int_addr, "onu_num": free_onu_number},
            "%s(config-if)#" % prompt,
        )

        # Apply int onu config
        template = get_onu_template_fn(*args, **kwargs)
        for line in template:
            self.ch.do_cmd(line, "%s(config-if)#" % prompt)

        # Exit
        self.ch.do_cmd("exit", "%s(config)#" % prompt)

    def apply_zte_bot_conf(
        self,
        prompt: str,
        int_addr: str,
        free_onu_number: int,
        get_pon_mng_template_fn=get_pon_mng_template,
        *args,
        **kwargs,
    ) -> None:
        # Enter to pon-onu-mng
        self.ch.do_cmd(
            "pon-onu-mng gpon-onu_%(int_addr)s:%(onu_num)d" % {"int_addr": int_addr, "onu_num": free_onu_number},
            "%s(gpon-onu-mng)#" % prompt,
        )

        # Apply config to pon-onu-mng
        for line in get_pon_mng_template_fn(*args, **kwargs):
            self.ch.do_cmd(line, "%s(gpon-onu-mng)#" % prompt)

        # Exit
        self.ch.do_cmd("exit", "%s(config)#" % prompt)
