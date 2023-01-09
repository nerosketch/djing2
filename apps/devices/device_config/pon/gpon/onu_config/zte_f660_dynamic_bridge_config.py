from devices.device_config import base
from .zte_f660_static_bridge_config import ZteF660BridgeStaticScriptModule, VlanList, get_ports_config


def _get_onu_template(all_vids: VlanList, onu_mac: str, *args, **kwargs) -> tuple:
    vids = ",".join(map(str, all_vids))
    return (
        "sn-bind enable sn",
        "tcont 1 profile HSI_100",
        "gemport 1 unicast tcont 1 dir both",
        "security storm-control broadcast rate 32 direction egress vport 1",
        "security storm-control broadcast rate 32 direction ingress vport 1",
        "switchport mode trunk vport 1",
        f"switchport vlan {vids} tag vport 1",
        "port-location format flexible-syntax vport 1",
        "port-location sub-option remote-id enable vport 1",
        "port-location sub-option remote-id name %s vport 1" % onu_mac,
        "dhcp-option82 enable vport 1",
        "dhcp-option82 trust true replace vport 1",
        "ip dhcp snooping enable vport 1",
    )


def _get_onu_mng_template(all_vids: VlanList, config: base.DeviceOnuConfigTemplateSchema, *args, **kwargs):
    all_vids = ",".join(map(str, set(all_vids)))
    vlan_config = config.vlanConfig

    ports_config = get_ports_config(vlan_config)

    return (
        [
            f"service HSI type internet gemport 1 vlan {all_vids}",
            "loop-detect ethuni eth_0/1 enable",
            "loop-detect ethuni eth_0/2 enable",
            "loop-detect ethuni eth_0/3 enable",
            "loop-detect ethuni eth_0/4 enable",
            "interface pots pots_0/1 state lock",
            "interface pots pots_0/2 state lock",
            "interface wifi wifi_0/1 state lock",
        ]
        + ports_config
        + [
            "dhcp-ip ethuni eth_0/1 from-internet",
            "dhcp-ip ethuni eth_0/2 from-internet",
            "dhcp-ip ethuni eth_0/3 from-internet",
            "dhcp-ip ethuni eth_0/4 from-internet",
        ]
    )


class ZteF660BridgeDynamicScriptModule(ZteF660BridgeStaticScriptModule):
    title = "Zte ONU F660 Dynamic Bridge"
    short_code = "zte_f660_bridge_d"

    def apply_zte_bot_conf(self, get_pon_mng_template_fn=_get_onu_mng_template, *args, **kwargs) -> None:
        return super().apply_zte_bot_conf(get_pon_mng_template_fn=get_pon_mng_template_fn, *args, **kwargs)

    def apply_zte_top_conf(self, get_onu_template_fn=_get_onu_template, *args, **kwargs) -> None:
        return super().apply_zte_top_conf(get_onu_template_fn=get_onu_template_fn, *args, **kwargs)
