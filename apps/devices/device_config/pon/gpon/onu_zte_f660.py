import re
from typing import Optional

from django.utils.translation import gettext_lazy as _

from djing2.lib import safe_int, process_lock_decorator
from devices.device_config.base import DeviceConsoleError, Vlan
from devices.device_config import expect_util
from .onu_config.zte_onu import ZteOnuDeviceConfigType
from . import zte_utils
from ..epon.epon_bdcom_fora import EPON_BDCOM_FORA, DefaultVlanDC
from ..pon_device_strategy import PonONUDeviceStrategyContext
from ...base_device_strategy import SNMPWorker

_DEVICE_UNIQUE_CODE = 6


@process_lock_decorator(lock_name="zte_olt")
def _remove_zte_onu_from_olt(zte_ip_addr: str, telnet_login: str, telnet_passw: str,
                             telnet_prompt: str, snmp_info: str, *args, **kwargs):
    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise expect_util.ExpectValidationError("ip address for zte not valid")

    rack_num, fiber_num, onu_num = zte_utils.zte_onu_conv_from_onu(snmp_info)
    int_addr = "1/%d/%d" % (rack_num, fiber_num)

    # Входим
    ch = ZteOnuDeviceConfigType.login_into_olt(zte_ip_addr, telnet_login, telnet_passw, telnet_prompt)

    # enter to config
    ch.do_cmd("conf t", "%s(config)#" % telnet_prompt)

    # go to olt interface
    ch.do_cmd("interface gpon-olt_%s" % int_addr, "%s(config-if)#" % telnet_prompt)

    # remove onu register from olt fiber
    ch.do_cmd("no onu %d" % onu_num, "%s(config-if)#" % telnet_prompt)

    # Exit
    ch.do_cmd("exit", "%s(config)#" % telnet_prompt)
    ch.do_cmd("exit", "%s#" % telnet_prompt)
    ch.sendline("exit")
    ch.close()
    return True


class OnuZTE_F660(EPON_BDCOM_FORA):
    description = "Zte ONU F660"
    tech_code = "zte_onu"
    ports_len = 4

    def get_details(self, sn_prefix='ZTEG', mac_prefix='45:47') -> Optional[dict]:
        dev = self.model_instance
        if dev is None:
            return {}
        snmp_extra = dev.snmp_extra
        if not snmp_extra:
            return {}

        parent = dev.parent_dev
        if not parent:
            return {}

        fiber_num, onu_num = zte_utils.split_snmp_extra(snmp_extra)
        fiber_addr = "%d.%d" % (fiber_num, onu_num)

        snmp = SNMPWorker(hostname=parent.ip_address, community=str(parent.man_passw))

        signal = safe_int(snmp.get_item(".1.3.6.1.4.1.3902.1012.3.50.12.1.1.10.%s.1" % fiber_addr))
        # distance = self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.18.%s.1' % fiber_addr)

        sn = snmp.get_item_plain(".1.3.6.1.4.1.3902.1012.3.28.1.1.5.%s" % fiber_addr)
        if sn is not None:
            if isinstance(sn, bytes):
                sn = f"{sn_prefix}%s" % "".join("%.2X" % int(x) for x in sn[-4:])
            else:
                sn = f"{sn_prefix}%s" % "".join("%.2X" % ord(x) for x in sn[-4:])

        raw_status = snmp.get_item(".1.3.6.1.4.1.3902.1012.3.50.12.1.1.1.%s.1" % fiber_addr)

        status_map = {1: "ok", 2: "down"}
        return {
            "status": status_map.get(
                safe_int(raw_status), "unknown"
            ),
            "signal": zte_utils.conv_zte_signal(signal),
            "mac": zte_utils.sn_to_mac(sn, prefix=mac_prefix),
            "info": (
                (_("name"), snmp.get_item(".1.3.6.1.4.1.3902.1012.3.28.1.1.3.%s" % fiber_addr)),
                # 'distance': safe_float(distance) / 10,
                # 'ip_addr': self.get_item('.1.3.6.1.4.1.3902.1012.3.50.16.1.1.10.%s' % fiber_addr),
                (_("vlans"), snmp.get_item(".1.3.6.1.4.1.3902.1012.3.50.15.100.1.1.7.%s.1.1" % fiber_addr)),
                (_("serial"), sn),
                (_("onu_type"), snmp.get_item(".1.3.6.1.4.1.3902.1012.3.28.1.1.1.%s" % fiber_addr)),
            ),
        }

    def default_vlan_info(self) -> list[DefaultVlanDC]:
        default_vid = 1
        dev = self.model_instance
        if dev and dev.parent_dev and dev.parent_dev.extra_data:
            default_vid = dev.parent_dev.extra_data.get("default_vid", 1)
        def_vids = [Vlan(vid=default_vid, native=True)]
        return [
            DefaultVlanDC(port=1, vids=def_vids),
            DefaultVlanDC(port=2, vids=def_vids),
            DefaultVlanDC(port=3, vids=def_vids),
            DefaultVlanDC(port=4, vids=def_vids),
        ]

    def read_onu_vlan_info(self):
        dev = self.model_instance
        if dev is None:
            return []
        snmp_extra = dev.snmp_extra
        if not snmp_extra:
            return self.default_vlan_info()
        fiber_num, onu_num = zte_utils.split_snmp_extra(snmp_extra)

        parent = dev.parent_dev
        if not parent:
            return []
        snmp = SNMPWorker(hostname=parent.ip_address, community=str(parent.man_passw))

        def _get_access_vlan(port_num: int) -> int:
            return safe_int(
                snmp.get_item(
                    ".1.3.6.1.4.1.3902.1012.3.50.15.100.1.1.4.%(fiber_num)d.%(onu_num)d.1.%(port_num)d"
                    % {"port_num": port_num, "fiber_num": fiber_num, "onu_num": onu_num}
                )
            )

        def _get_trunk_vlans(port_num: int) -> list[Vlan]:
            trunk_vlans = snmp.get_item(
                ".1.3.6.1.4.1.3902.1012.3.50.15.100.1.1.7.%(fiber_num)d.%(onu_num)d.1.%(port_num)d"
                % {"port_num": port_num, "fiber_num": fiber_num, "onu_num": onu_num}
            )
            if not trunk_vlans:
                return []

            def _rng(r):
                if not r:
                    return
                if b"-" in r:
                    a1, a2 = r.split(b"-")
                    return range(int(a1), int(a2))
                else:
                    return int(r)

            vids = (
                tuple(t) if isinstance(t, range) else (t,) for t in map(_rng, filter(bool, trunk_vlans.split(b",")))
            )
            return [Vlan(vid=v, native=False) for i in vids for v in i]

        # Result example
        # [
        #     {
        #         'port': 1,
        #         'vids': [
        #             {'vid': 143, 'native': True},
        #             {'vid': 144, 'native': False},
        #             {'vid': 145, 'native': False},
        #         ]
        #     }
        # ]
        return (
            DefaultVlanDC(
                port=i,
                vids=[Vlan(
                    vid=_get_access_vlan(port_num=i),
                    native=True
                )] + _get_trunk_vlans(port_num=i),
            )
            for i in range(1, self.ports_len+1)
        )

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # for example 268501760.5
        zte_utils.split_snmp_extra(v)

    def remove_from_olt(self, extra_data: dict, sn_prefix='ZTEG', mac_prefix='45:47', **kwargs):
        dev = self.model_instance
        if not dev:
            return False
        if not dev.parent_dev or not dev.snmp_extra:
            return False
        telnet = extra_data.get("telnet")
        if not telnet:
            return False

        parent = dev.parent_dev

        fiber_num, onu_num = zte_utils.split_snmp_extra(str(dev.snmp_extra))
        fiber_addr = "%d.%d" % (fiber_num, onu_num)
        with SNMPWorker(hostname=parent.ip_address, community=str(parent.man_passw)) as snmp:
            sn = snmp.get_item_plain(".1.3.6.1.4.1.3902.1012.3.28.1.1.5.%s" % fiber_addr)
        if sn is not None:
            if isinstance(sn, str):
                sn = f"{sn_prefix}%s" % "".join("%.2X" % ord(x) for x in sn[-4:])
            else:
                sn = f"{sn_prefix}%s" % "".join("%.2X" % x for x in sn[-4:])
            sn_mac = zte_utils.sn_to_mac(sn, prefix=mac_prefix)
            if str(dev.mac_addr) != sn_mac:
                raise expect_util.ExpectValidationError(_("Mac of device not equal mac by snmp"))
            return _remove_zte_onu_from_olt(
                zte_ip_addr=str(dev.parent_dev.ip_address),
                telnet_login=telnet.get("login"),
                telnet_passw=telnet.get("password"),
                telnet_prompt=telnet.get("prompt"),
                snmp_info=str(dev.snmp_extra),
            )
        raise DeviceConsoleError(_("Could not fetch serial for onu"))

    def get_fiber_str(self):
        dev = self.model_instance
        if not dev:
            return
        dat = dev.snmp_extra
        if dat and "." in dat:
            rack_num, fiber_num, onu_num = zte_utils.zte_onu_conv_from_onu(dat)
            return "gpon-onu_1/%d/%d:%s" % (rack_num, fiber_num, onu_num)
        return super().get_fiber_str()

    @staticmethod
    def get_config_types():
        from .onu_config.zte_f660_router_config import ZteF660RouterScriptModule
        from .onu_config.zte_f660_static_bridge_config import ZteF660BridgeStaticScriptModule
        from .onu_config.zte_f660_dynamic_bridge_config import ZteF660BridgeDynamicScriptModule

        return [
            ZteF660RouterScriptModule,
            ZteF660BridgeStaticScriptModule,
            ZteF660BridgeDynamicScriptModule
        ]

    def find_onu(self, *args, **kwargs):
        dev = self.model_instance
        parent = dev.parent_dev
        if parent is not None:
            mac = dev.mac_addr
            extra_data = dict(parent.extra_data)

            serial_num = "ZTEG" + "".join("%.2x" % i for i in mac[-4:]).upper()

            telnet = extra_data.get("telnet")
            hostname=parent.ip_address
            prompt = telnet.get("prompt")
            # Enter
            ch = ZteOnuDeviceConfigType.login_into_olt(
                hostname=hostname,
                login=telnet.get("login"),
                password=telnet.get("password"),
                prompt=prompt
            )

            # find onu on olt
            ch.do_cmd("show gpon onu by sn %s" % serial_num, "%s#" % prompt)
            for line in ch.get_lines_before():
                if line.startswith('gpon-onu'):
                    # Found onu
                    onu = zte_utils.parse_onu_name(line)
                    onu_num = zte_utils.zte_onu_conv_to_num(
                        rack_num=int(onu['rack_num']),
                        fiber_num=int(onu['fiber_num']),
                        port_num=int(onu['onu_num'])
                    )
                    # Exit
                    ch.sendline("exit")
                    ch.close()
                    return onu_num, None

            # Exit
            ch.sendline("exit")
            ch.close()

            # Not found onu
            return None, _('Onu with mac "%(onu_mac)s" not found on OLT') % {"onu_mac": mac}

        return None, _("Parent device not found")


PonONUDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, OnuZTE_F660)
