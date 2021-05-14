from django.utils.translation import gettext_lazy as _

from devices.device_config import expect_util
from . import zte_onu
from ...utils import VlanList


def _get_onu_template(all_vids: VlanList, *args, **kwargs) -> tuple:
    vids = ",".join(map(str, all_vids))
    template = (
        "sn-bind enable sn",
        "tcont 1 profile HSI_100",
        "gemport 1 unicast tcont 1 dir both",
        "security storm-control broadcast rate 64 direction ingress vport 1",
        "security storm-control broadcast rate 64 direction egress vport 1",
        "switchport mode trunk vport 1",
        f"switchport vlan {vids} tag vport 1",
    )
    return template


def _get_pon_mng_template(all_vids: VlanList, config: dict, *args, **kwargs) -> list:
    all_vids = ",".join(map(str, set(all_vids)))
    vlan_config = config.get("vlanConfig")
    vids = vlan_config[0].get("vids")
    native_vids = (vid.get("vid") for vid in vids if vid.get("native", False))
    native_vids = list(set(native_vids))
    trunk_vids = (vid.get("vid") for vid in vids if not vid.get("native", False))
    trunk_vids = list(set(trunk_vids))

    native_vids_len = len(native_vids)
    trunk_vids_len = len(trunk_vids)

    if native_vids_len > 1:
        raise expect_util.ExpectValidationError(_("Multiple native vid is not allowed on one port"))

    ports_config = []

    if native_vids_len == 1:
        if trunk_vids_len > 0:
            # Trunk with access port, Hybrid
            ports_config.extend(
                [
                    "vlan port eth_0/1 mode hybrid def-vlan %d" % native_vids[0],
                    "vlan port eth_0/1 vlan %s" % ",".join(map(str, trunk_vids)),
                ]
            )
        elif trunk_vids_len == 0:
            # Only Access port
            ports_config.append("vlan port eth_0/1 mode tag vlan %d" % native_vids[0])
    elif native_vids_len == 0:
        if trunk_vids_len > 0:
            # Only trunk port
            ports_config.extend(
                [
                    "vlan port eth_0/1 mode trunk",
                    "vlan port eth_0/1 vlan %s" % ",".join(map(str, trunk_vids)),
                ]
            )
        elif trunk_vids_len == 0:
            # Without vlan config, type default vlan
            ports_config.append("vlan port eth_0/1 mode tag vlan 1")

    return (
        [
            f"service HSI type internet gemport 1 vlan {all_vids}",
            "loop-detect ethuni eth_0/1 enable",
        ]
        + ports_config
        + ["dhcp-ip ethuni eth_0/1 forbidden"]
    )


class ZteF601StaticScriptModule(zte_onu.ZteOnuDeviceConfigType):
    title = "Zte F601 static"
    short_code = "zte_f601_static"
    accept_vlan = True
    zte_type = "ZTE-F601"

    def apply_zte_top_conf(self, prompt: str, free_onu_number: int, int_addr: str, *args, **kwargs) -> None:
        # Enter to int onu
        self.ch.do_cmd(
            "int gpon-onu_%(int_addr)s:%(onu_num)d" % {"int_addr": int_addr, "onu_num": free_onu_number},
            "%s(config-if)#" % prompt,
        )

        # Apply int onu config
        template = _get_onu_template(*args, **kwargs)
        for line in template:
            self.ch.do_cmd(line, "%s(config-if)#" % prompt)

        # Exit
        self.ch.do_cmd("exit", "%s(config)#" % prompt)

    def apply_zte_bot_conf(self, prompt: str, int_addr: str, free_onu_number: int, *args, **kwargs) -> None:
        # Enter to pon-onu-mng
        self.ch.do_cmd(
            "pon-onu-mng gpon-onu_%(int_addr)s:%(onu_num)d" % {"int_addr": int_addr, "onu_num": free_onu_number},
            "%s(gpon-onu-mng)#" % prompt,
        )

        # Apply config to pon-onu-mng
        for line in _get_pon_mng_template(*args, **kwargs):
            self.ch.do_cmd(line, "%s(gpon-onu-mng)#" % prompt)

        # Exit
        self.ch.do_cmd("exit", "%s(config)#" % prompt)
