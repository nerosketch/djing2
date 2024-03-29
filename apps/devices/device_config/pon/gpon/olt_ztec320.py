from dataclasses import dataclass
from typing import Iterable, Generator

from djing2.lib import RuTimedelta, safe_int, macbin2str, process_lock_decorator
from devices.device_config.base import Vlans, Vlan
from ..pon_device_strategy import PonOLTDeviceStrategyContext, FiberDataClass
from ..epon.bdcom_p3310c import BDCOM_P3310C
from ...base_device_strategy import SNMPWorker

_DEVICE_UNIQUE_CODE = 5


@dataclass
class UnregisteredUnitType:
    mac: str
    firmware_ver: str
    loid: str
    loid_passw: str
    fiber: str
    sn: str


class ZTE_C320(BDCOM_P3310C):
    description = "OLT ZTE C320"
    ports_len = 8

    def get_fibers(self) -> Generator[FiberDataClass, None, None]:
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        fibers = (
            FiberDataClass(
                fb_id=int(fiber_id),
                fb_name=fiber_name,
                fb_onu_num=safe_int(snmp.get_item(".1.3.6.1.4.1.3902.1012.3.13.1.1.13.%d" % int(fiber_id))),
                # 'fb_active_onu': -1,
                # Temperature GPON SFP module
                # 'fb_temp': safe_float(self.get_item(
                #     '.1.3.6.1.4.1.3902.1015.3.1.13.1.12.%d' % safe_int(fiber_id)
                # )) / 1000.0,
                # Power of laser GPON SFP Module
                # 'fb_power': safe_float(self.get_item(
                #     '.1.3.6.1.4.1.3902.1015.3.1.13.1.9.%d' % safe_int(fiber_id)
                # )) / 1000.0
            )
            for fiber_name, fiber_id in snmp.get_list_keyval(".1.3.6.1.4.1.3902.1012.3.13.1.1.1")
        )
        return fibers

    def get_details(self) -> dict:
        dev = self.model_instance
        parent = dev.parent_dev
        if not parent:
            return {}
        with SNMPWorker(hostname=parent.ip_address, community=str(parent.man_passw)) as snmp:
            details = {
                "disk_total": snmp.get_item(".1.3.6.1.4.1.3902.1015.14.1.1.1.7.1.1.4.0.5.102.108.97.115.104.1"),
                "disk_free": snmp.get_item(".1.3.6.1.4.1.3902.1015.14.1.1.1.8.1.1.4.0.5.102.108.97.115.104.1"),
                "fname": snmp.get_item(".1.3.6.1.4.1.3902.1015.2.1.2.2.1.2.1.1.1"),
                "fver": snmp.get_item(".1.3.6.1.4.1.3902.1015.2.1.2.2.1.4.1.1.1"),
            }
        details.update(super().get_details())
        return details

    @process_lock_decorator()
    def get_ports_on_fiber(self, fiber_num: int) -> Iterable:
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        onu_types = snmp.get_list_keyval(".1.3.6.1.4.1.3902.1012.3.28.1.1.1.%d" % fiber_num)
        onu_ports = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.28.1.1.2.%d" % fiber_num)
        # onu_signals = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.50.12.1.1.10.%d" % fiber_num)
        onu_states = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.50.12.1.1.1.%d" % fiber_num)

        # Real sn in last 3 octets
        onu_sns = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.28.1.1.5.%d" % fiber_num)
        onu_prefixs = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.50.11.2.1.1.%d" % fiber_num)

        status_map = {1: "ok", 2: "down"}

        onu_list = (
            {
                "onu_type": onu_type_num[0],
                "onu_port": onu_port,
                "onu_signal": 0,  # conv_zte_signal(onu_signal),
                "onu_sn": onu_prefix.decode() + "".join("%.2X" % i for i in onu_sn[-4:]),  # Real sn in last 4 octets,
                "snmp_extra": "%d.%d" % (fiber_num, safe_int(onu_type_num[1])),
                "onu_state": status_map.get(safe_int(onu_state), "unknown"),
            }
            for onu_type_num, onu_port, onu_sn, onu_prefix, onu_state in zip(
                onu_types, onu_ports, onu_sns, onu_prefixs, onu_states
            )
        )

        return onu_list

    def get_units_unregistered(self, fiber: FiberDataClass) -> Generator[UnregisteredUnitType, None, None]:
        fiber_num = fiber.fb_id
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        sn_list = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.13.3.1.2.%d" % fiber_num)
        firmware_ver = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.13.3.1.11.%d" % fiber_num)
        loid_passws = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.13.3.1.9.%d" % fiber_num)
        loids = snmp.get_list(".1.3.6.1.4.1.3902.1012.3.13.3.1.8.%d" % fiber_num)

        return (
            UnregisteredUnitType(
                mac=macbin2str(sn[-6:]),
                firmware_ver=frm_ver,
                loid_passw=loid_passw,
                loid=loid,
                fiber=fiber.fb_name,
                sn=sn[:4].decode() + ''.join('%.2x' % i for i in sn[-4:]).upper(),
            )
            for frm_ver, loid_passw, loid, sn in zip(firmware_ver, loid_passws, loids, sn_list)
        )

    def get_uptime(self):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            up_timestamp = safe_int(snmp.get_item(".1.3.6.1.2.1.1.3.0"))
        tm = RuTimedelta(seconds=up_timestamp / 100)
        return str(tm)

    def get_long_description(self):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.get_item(".1.3.6.1.2.1.1.1.0")

    def get_hostname(self):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.get_item(".1.3.6.1.2.1.1.5.0")

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

    @process_lock_decorator()
    def read_all_vlan_info(self) -> Vlans:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            for vid, vname in snmp.get_list_keyval(".1.3.6.1.4.1.3902.1015.20.2.1.2"):
                yield Vlan(vid=int(vid), title=vname)

    # def attach_vlans_to_uplink(self, vids: Iterable[int], stack_num: int,
    #                            rack_num: int, port_num: int) -> None:
    #     self.write('int gei_%d/%d/%d' % (stack_num, rack_num, port_num))
    #     self.read_until('(config-if)#')
    #     for v in vids:
    #         self.write('switchport vlan %d tag' % v)
    #         self.read_until('(config-if)#')
    #     self.write('exit')
    #     self.read_until('(config)#')


# class OLT_ZTE_C320_ONU:
#     def __init__(self, bt: ZTE_C320, stack_num: int, rack_num: int, fiber_num: int, onu_num: int):
#         self.bt: ZTE_C320 = bt
#         self.stack_num = stack_num
#         self.rack_num = rack_num
#         self.fiber_num = fiber_num
#         self.onu_num = onu_num
#
#     def __enter__(self):
#         self.bt.write("int gpon-onu_%d/%d/%d:%d" % (self.stack_num, self.rack_num, self.fiber_num, self.onu_num))
#         self._read_until_if()
#
#     def _read_until_if(self) -> bytes:
#         return self.bt.read_until("(config-if)#")
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.bt.write("exit")
#         self.bt.read_until("(config)#")


# class OLT_ZTE_C320_Fiber:
#     def __init__(self, bt: ZTE_C320, stack_num: int, rack_num: int, fiber_num):
#         self.bt: ZTE_C320 = bt
#         self.stack_num = stack_num
#         self.rack_num = rack_num
#         self.fiber_num = fiber_num
#
#     def __enter__(self):
#         self.bt.write("int gpon-olt_%d/%d/%d" % (self.stack_num, self.rack_num, self.fiber_num))
#         self._read_until_if()
#
#     def _read_until_if(self) -> bytes:
#         return self.bt.read_until("(config-if)#")
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.bt.write("exit")
#         self.bt.read_until("(config)#")
#
#     def remove_onu(self, onu_num: int) -> None:
#         self.bt.write("no onu %d" % onu_num)
#         self._read_until_if()
#
#     def custom_command(self, cmd: str, expect_after: str) -> None:
#         self.bt.write(cmd)
#         self.bt.read_until(expect_after)


PonOLTDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, ZTE_C320)
