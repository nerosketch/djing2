from typing import Iterable

from djing2.lib import RuTimedelta, safe_int, macbin2str, process_lock
from .zte_utils import conv_zte_signal
from ..epon import BDCOM_P3310C
from devices.device_config.base import Vlans, Vlan


class ZTE_C320(BDCOM_P3310C):
    description = "OLT ZTE C320"

    def get_fibers(self):
        fibers = (
            {
                "fb_id": int(fiber_id),
                "fb_name": fiber_name,
                "fb_onu_num": safe_int(self.get_item(".1.3.6.1.4.1.3902.1012.3.13.1.1.13.%d" % int(fiber_id))),
                # 'fb_active_onu': -1,
                # Temperature GPON SFP module
                # 'fb_temp': safe_float(self.get_item(
                #     '.1.3.6.1.4.1.3902.1015.3.1.13.1.12.%d' % safe_int(fiber_id)
                # )) / 1000.0,
                # Power of laser GPON SFP Module
                # 'fb_power': safe_float(self.get_item(
                #     '.1.3.6.1.4.1.3902.1015.3.1.13.1.9.%d' % safe_int(fiber_id)
                # )) / 1000.0
            }
            for fiber_name, fiber_id in self.get_list_keyval(".1.3.6.1.4.1.3902.1012.3.13.1.1.1")
        )
        return fibers

    def get_details(self) -> dict:
        details = {
            "disk_total": self.get_item(".1.3.6.1.4.1.3902.1015.14.1.1.1.7.1.1.4.0.5.102.108.97.115.104.1"),
            "disk_free": self.get_item(".1.3.6.1.4.1.3902.1015.14.1.1.1.8.1.1.4.0.5.102.108.97.115.104.1"),
            "fname": self.get_item(".1.3.6.1.4.1.3902.1015.2.1.2.2.1.2.1.1.1"),
            "fver": self.get_item(".1.3.6.1.4.1.3902.1015.2.1.2.2.1.4.1.1.1"),
        }
        details.update(super().get_details())
        return details

    @process_lock()
    def get_ports_on_fiber(self, fiber_num: int) -> Iterable:
        onu_types = self.get_list_keyval(".1.3.6.1.4.1.3902.1012.3.28.1.1.1.%d" % fiber_num)
        onu_ports = self.get_list(".1.3.6.1.4.1.3902.1012.3.28.1.1.2.%d" % fiber_num)
        onu_signals = self.get_list(".1.3.6.1.4.1.3902.1012.3.50.12.1.1.10.%d" % fiber_num)
        onu_states = self.get_list(".1.3.6.1.4.1.3902.1012.3.50.12.1.1.1.%d" % fiber_num)

        # Real sn in last 3 octets
        onu_sns = self.get_list(".1.3.6.1.4.1.3902.1012.3.28.1.1.5.%d" % fiber_num)
        onu_prefixs = self.get_list(".1.3.6.1.4.1.3902.1012.3.50.11.2.1.1.%d" % fiber_num)

        status_map = {1: "ok", 2: "down"}

        onu_list = (
            {
                "onu_type": onu_type_num[0],
                "onu_port": onu_port,
                "onu_signal": conv_zte_signal(onu_signal),
                "onu_sn": onu_prefix.decode() + "".join("%.2X" % i for i in onu_sn[-4:]),  # Real sn in last 4 octets,
                "snmp_extra": "%d.%d" % (fiber_num, safe_int(onu_type_num[1])),
                "onu_state": status_map.get(safe_int(onu_state), "unknown"),
            }
            for onu_type_num, onu_port, onu_signal, onu_sn, onu_prefix, onu_state in zip(
                onu_types, onu_ports, onu_signals, onu_sns, onu_prefixs, onu_states
            )
        )

        return onu_list

    def get_units_unregistered(self, fiber_num: int) -> Iterable:
        sn_num_list = self.get_list_keyval(".1.3.6.1.4.1.3902.1012.3.13.3.1.2.%d" % fiber_num)
        firmware_ver = self.get_list(".1.3.6.1.4.1.3902.1012.3.13.3.1.11.%d" % fiber_num)
        loid_passws = self.get_list(".1.3.6.1.4.1.3902.1012.3.13.3.1.9.%d" % fiber_num)
        loids = self.get_list(".1.3.6.1.4.1.3902.1012.3.13.3.1.8.%d" % fiber_num)

        return (
            {
                "mac": macbin2str(sn[-6:]),
                "firmware_ver": frm_ver,
                "loid_passw": loid_passw,
                "loid": loid,
                "sn": "ZTEG" + "".join("%.2x" % i for i in sn[-4:]).upper(),
            }
            for frm_ver, loid_passw, loid, (sn, num) in zip(firmware_ver, loid_passws, loids, sn_num_list)
        )

    def get_uptime(self):
        up_timestamp = safe_int(self.get_item(".1.3.6.1.2.1.1.3.0"))
        tm = RuTimedelta(seconds=up_timestamp / 100)
        return str(tm)

    def get_long_description(self):
        return self.get_item(".1.3.6.1.2.1.1.1.0")

    def get_hostname(self):
        return self.get_item(".1.3.6.1.2.1.1.5.0")

    #############################
    #      Telnet access
    #############################

    # def login(self, login: str, password: str, *args, **kwargs) -> bool:
    #     super().login(
    #         login_prompt=b'Username:',
    #         login=login,
    #         password_prompt=b'Password:',
    #         password=password
    #     )
    #     out = self.read_until(self.prompt)
    #     return b'bad password' in out

    @process_lock()
    def read_all_vlan_info(self) -> Vlans:
        for vid, vname in self.get_list_keyval(".1.3.6.1.4.1.3902.1015.20.2.1.2"):
            yield Vlan(vid=int(vid), title=vname)

    # def create_vlans(self, vlan_list: Vlans) -> bool:
    #     for v in vlan_list:
    #         self.write('vlan %d' % v.vid)
    #         self.read_until('(config-vlan)#')
    #         self.write('name %s' % self._normalize_name(v.title))
    #         self.read_until('(config-vlan)#')
    #         self.write('exit')
    #         self.read_until('(config)#')
    #     return True

    # def delete_vlans(self, vlan_list: Vlans) -> bool:
    #     for v in vlan_list:
    #         self.write('no vlan %d' % v.vid)
    #         self.read_until('(config)#')
    #     return True

    # def attach_vlans_to_uplink(self, vids: Iterable[int], stack_num: int,
    #                            rack_num: int, port_num: int) -> None:
    #     self.write('int gei_%d/%d/%d' % (stack_num, rack_num, port_num))
    #     self.read_until('(config-if)#')
    #     for v in vids:
    #         self.write('switchport vlan %d tag' % v)
    #         self.read_until('(config-if)#')
    #     self.write('exit')
    #     self.read_until('(config)#')


class OLT_ZTE_C320_ONU:
    def __init__(self, bt: ZTE_C320, stack_num: int, rack_num: int, fiber_num: int, onu_num: int):
        self.bt: ZTE_C320 = bt
        self.stack_num = stack_num
        self.rack_num = rack_num
        self.fiber_num = fiber_num
        self.onu_num = onu_num

    def __enter__(self):
        self.bt.write("int gpon-onu_%d/%d/%d:%d" % (self.stack_num, self.rack_num, self.fiber_num, self.onu_num))
        self._read_until_if()

    def _read_until_if(self) -> bytes:
        return self.bt.read_until("(config-if)#")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.bt.write("exit")
        self.bt.read_until("(config)#")


class OLT_ZTE_C320_Fiber:
    def __init__(self, bt: ZTE_C320, stack_num: int, rack_num: int, fiber_num):
        self.bt: ZTE_C320 = bt
        self.stack_num = stack_num
        self.rack_num = rack_num
        self.fiber_num = fiber_num

    def __enter__(self):
        self.bt.write("int gpon-olt_%d/%d/%d" % (self.stack_num, self.rack_num, self.fiber_num))
        self._read_until_if()

    def _read_until_if(self) -> bytes:
        return self.bt.read_until("(config-if)#")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.bt.write("exit")
        self.bt.read_until("(config)#")

    def remove_onu(self, onu_num: int) -> None:
        self.bt.write("no onu %d" % onu_num)
        self._read_until_if()

    def custom_command(self, cmd: str, expect_after: str) -> None:
        self.bt.write(cmd)
        self.bt.read_until(expect_after)
