from typing import List

from django.utils.translation import gettext_lazy as _

from devices.device_config import expect_util
from .zte_f601_bridge_config import ZteF601BridgeScriptModule


VlanList = List[int]


def _get_onu_template(all_vids: VlanList, *args, **kwargs) -> tuple:
    vids = ",".join(map(str, all_vids))
    return (
        "sn-bind enable sn",
        "tcont 1 profile HSI_100",
        "gemport 1 unicast tcont 1 dir both",
        "security storm-control broadcast rate 8 direction egress vport 1",
        "security storm-control broadcast rate 8 direction ingress vport 1",
        "switchport mode trunk vport 1",
        f"switchport vlan {vids} tag vport 1",
    )


def _get_onu_mng_template(all_vids: VlanList, config: dict, *args, **kwargs):
    all_vids = ",".join(map(str, set(all_vids)))
    vlan_config = config.get("vlanConfig")

    ports_config = []

    for port_conf in vlan_config:
        port_num = port_conf.get("port")

        vids = port_conf.get("vids")
        if not vids:
            continue

        native_vids = (vid.get("vid") for vid in vids if vid.get("native", False))
        native_vids = list(set(native_vids))
        trunk_vids = (vid.get("vid") for vid in vids if not vid.get("native", False))
        trunk_vids = list(set(trunk_vids))

        native_vids_len = len(native_vids)
        trunk_vids_len = len(trunk_vids)

        if native_vids_len > 1:
            raise expect_util.ExpectValidationError(_("Multiple native vid is not allowed on one port"))

        if native_vids_len == 1:
            if trunk_vids_len > 0:
                # Trunk with access port, Hybrid
                ports_config.extend(
                    [
                        "vlan port eth_0/%d mode hybrid def-vlan %d" % (port_num, native_vids[0]),
                        "vlan port eth_0/%d vlan %s" % (port_num, ",".join(map(str, trunk_vids))),
                    ]
                )
            elif trunk_vids_len == 0:
                # Only Access port
                ports_config.append("vlan port eth_0/%d mode tag vlan %d" % (port_num, native_vids[0]))
        elif native_vids_len == 0:
            if trunk_vids_len > 0:
                # Only trunk port
                ports_config.extend(
                    [
                        "vlan port eth_0/%d mode trunk" % port_num,
                        "vlan port eth_0/%d vlan %s" % (port_num, ",".join(map(str, trunk_vids))),
                    ]
                )
            elif trunk_vids_len == 0:
                # Without vlan config, type default vlan
                ports_config.append("vlan port eth_0/%d mode tag vlan 1" % port_num)

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
            "dhcp-ip ethuni eth_0/1 forbidden",
            "dhcp-ip ethuni eth_0/2 forbidden",
            "dhcp-ip ethuni eth_0/3 forbidden",
            "dhcp-ip ethuni eth_0/4 forbidden",
        ]
    )


class ZteF660BridgeStaticScriptModule(ZteF601BridgeScriptModule):
    title = "Zte ONU F660 Static Bridge"
    short_code = "zte_f660_bridge"
    accept_vlan = True
    zte_type = "ZTE-F660"

    def apply_zte_bot_conf(self, *args, **kwargs) -> None:
        return super().apply_zte_bot_conf(get_pon_mng_template_fn=_get_onu_mng_template, *args, **kwargs)

    def apply_zte_top_conf(self, *args, **kwargs) -> None:
        return super().apply_zte_top_conf(get_onu_template_fn=_get_onu_template, *args, **kwargs)
