import math
from typing import Generator, Iterable, Dict

from django.utils.translation import gettext_lazy as _

from djing2.lib import safe_int, RuTimedelta, process_lock_decorator
from devices.device_config.base import (
    Vlans,
    Vlan,
    MacItem,
    Macs,
    DeviceImplementationError,
)
from ..switch_device_strategy import SwitchDeviceStrategyContext
from ..dlink.dgs_1100_10me import DlinkDGS1100_10ME
from ..switch_device_strategy import PortType
from ...base_device_strategy import SNMPWorker

_DEVICE_UNIQUE_CODE = 4


class EltexSwitch(DlinkDGS1100_10ME):
    description = _("Eltex switch")
    is_use_device_port = False
    has_attachable_to_customer = True
    tech_code = "eltex_sw"
    ports_len = 24

    @staticmethod
    def build_port(snmp, i: int, n: int):
        speed = safe_int(snmp.get_item(".1.3.6.1.2.1.2.2.1.5.%d" % n))
        return PortType(
            num=i,
            name=snmp.get_item(".1.3.6.1.2.1.31.1.1.1.18.%d" % n),
            status=snmp.get_item(".1.3.6.1.2.1.2.2.1.7.%d" % n) == 1,
            mac=snmp.get_item(".1.3.6.1.2.1.2.2.1.6.%d" % n),
            uptime=snmp.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % n),
            speed=speed,
        )

    def get_ports(self) -> tuple:
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        return tuple(self.build_port(snmp, i, n) for i, n in enumerate(range(49, self.ports_len + 49), 1))

    def get_device_name(self):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.get_item(".1.3.6.1.2.1.1.5.0")

    def get_uptime(self):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            uptimestamp = safe_int(snmp.get_item(".1.3.6.1.2.1.1.3.0"))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return tm

    def save_config(self) -> bool:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.set_multiple([
                ("1.3.6.1.4.1.89.87.2.1.3.1", 1, "i"),
                ("1.3.6.1.4.1.89.87.2.1.7.1", 2, "i"),
                ("1.3.6.1.4.1.89.87.2.1.8.1", 1, "i"),
                ("1.3.6.1.4.1.89.87.2.1.12.1", 3, "i"),
                ("1.3.6.1.4.1.89.87.2.1.17.1", 4, "i"),
            ])

    def reboot(self, save_before_reboot=False) -> bool:
        dev = self.model_instance
        if save_before_reboot:
            if not self.save_config():
                return False
            with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
                if not snmp.set("1.3.6.1.4.1.89.1.10.0", 8, snmp_type="t"):
                    return False
        else:
            with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
                if not snmp.set("1.3.6.1.4.1.89.1.10.0", 0, snmp_type="t"):
                    return False
        return True

    def port_disable(self, port_num: int):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            snmp.set_int_value("%s.%d" % (".1.3.6.1.2.1.2.2.1.7", port_num + 48), 2)

    def port_enable(self, port_num: int):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            snmp.set_int_value("%s.%d" % (".1.3.6.1.2.1.2.2.1.7", port_num + 48), 1)

    def read_port_vlan_info(self, port: int) -> Vlans:
        def _calc_ret(vlan_untagged_egress_oid, vlan_egress_bitmap, table_no) -> Vlans:
            vlan_untagged_egress = snmp.get_item(vlan_untagged_egress_oid)
            vlan_untagged_egress = list(self.parse_eltex_vlan_map(vlan_untagged_egress, table=table_no))
            is_native = next((v == 1 for i, v in enumerate(vlan_untagged_egress, 1) if i >= port), False)
            return (
                Vlan(vid=vid, title=self.get_vid_name(vid=vid), native=is_native)
                for vid in self.parse_eltex_vlan_map(vlan_egress_bitmap, table=table_no)
            )

        if port > self.ports_len or port < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)
        port = port + 48

        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))

        # rldot1qPortVlanStaticEgressList1to1024
        vlan_egress = snmp.get_item("1.3.6.1.4.1.89.48.68.1.1.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList1to1024
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.5.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=0,
            )

        # rldot1qPortVlanStaticEgressList1025to2048
        vlan_egress = snmp.get_item("1.3.6.1.4.1.89.48.68.1.2.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList1025to2048
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.6.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=1,
            )
        # rldot1qPortVlanStaticEgressList2049to3072
        vlan_egress = snmp.get_item("1.3.6.1.4.1.89.48.68.1.3.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList2049to3072
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.7.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=2,
            )
        # rldot1qPortVlanStaticEgressList3073to4094
        vlan_egress = snmp.get_item("1.3.6.1.4.1.89.48.68.1.4.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList3073to4094
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.8.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=3,
            )

    def read_all_vlan_info(self) -> Vlans:
        snmp_vid = 100000
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        while True:
            res = snmp.get_next(".1.3.6.1.2.1.2.2.1.1.%d" % snmp_vid)
            if res.snmp_type != "INTEGER":
                break
            vid = snmp_vid = safe_int(res.value)
            if vid < 100000 or vid > 104095:
                break
            vid = (vid - 100000) + 1
            name = self.get_vid_name(vid=vid)
            yield Vlan(vid=vid, title=name)

    @process_lock_decorator()
    def read_mac_address_port(self, port_num: int) -> Macs:
        if port_num > self.ports_len or port_num < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        try:
            ports_map = {int(i): n + 1 for n, i in enumerate(snmp.get_list(".1.3.6.1.2.1.2.2.1.1")) if int(i) > 0}
        except ValueError:
            return
        for fdb_port, oid in snmp.get_list_with_oid(".1.3.6.1.2.1.17.7.1.2.2.1.2"):
            real_fdb_port_num = ports_map.get(int(fdb_port))
            if port_num != real_fdb_port_num:
                continue
            vid = safe_int(oid[-7:-6][0])
            fdb_mac = ":".join("%.2x" % int(i) for i in oid[-6:])
            vid_name = self.get_vid_name(vid)
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=real_fdb_port_num)

    def read_mac_address_vlan(self, vid: int) -> Macs:
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        try:
            ports_map = {int(i): n + 1 for n, i in enumerate(snmp.get_list(".1.3.6.1.2.1.2.2.1.1")) if int(i) > 0}
        except ValueError:
            return
        for fdb_port, oid in snmp.get_list_with_oid(".1.3.6.1.2.1.17.7.1.2.2.1.2.%d" % vid):
            real_fdb_port_num = ports_map.get(int(fdb_port))
            fdb_mac = ":".join("%.2x" % int(i) for i in oid[-6:])
            vid_name = self.get_vid_name(vid)
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=real_fdb_port_num)

    @staticmethod
    def make_eltex_map_vlan(vids: Iterable[int]) -> Dict[int, bytes]:
        """
        https://eltex-co.ru/upload/iblock/f69/MES_configuration_and_monitoring_via_SNMP_1.1.48.11,%202.5.48.11,%202.2.14.6.pdf
        :param vids: Vlan id iterable collection
        :return: bytes bit map vlan representation by Eltex version
                 with index of table in dict key
        >>> EltexSwitch.make_eltex_map_vlan([3100])
        {3: b'\\x00\\x00\\x00\\x10\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'}
        >>> EltexSwitch.make_eltex_map_vlan([5, 6, 143, 152])
        {0: b'\\x0c\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x02
        \\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00
        \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'}
        """
        vids = list(set(vids))
        vids.sort()
        res = {}
        for vid in vids:
            if vid > 4095 or vid < 1:
                raise DeviceImplementationError("VID must be in range 1-%d" % 4095)
            table_no = int(math.floor(vid / 1024))
            vid -= int(math.floor(vid / 1024)) * 1024
            if res.get(table_no) is None:
                res[table_no] = 0
            res[table_no] |= 1 << (1024 - vid)
        for k in res.keys():
            res[k] = res[k].to_bytes(128, "big")
        return res

    @staticmethod
    def parse_eltex_vlan_map(bitmap: bytes, table: int = 0) -> Generator[int, None, None]:
        """
        https://eltex-co.ru/upload/iblock/f69/MES_configuration_and_monitoring_via_SNMP_1.1.48.11,%202.5.48.11,%202.2.14.6.pdf
        :param bitmap: str bit map vlan representation by Eltex version
        :param table: Value from 0 to 3. In which table can find vlan id list
        :return: VID, vlan id
        >>> bitmap = (\
                '\\x08\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
                '\\x00\\x02\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
                '\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
                '\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
                '\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
                '\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
                '\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
                '\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00'\
            )
        >>> tuple(EltexSwitch.parse_eltex_vlan_map(bitmap))
        (5, 143, 152)
        """
        if not isinstance(bitmap, bytes):
            raise TypeError('"bitmap" must be an instance of bytes')
        if table < 0 or table > 3:
            raise DeviceImplementationError("table must be in range 1-3")
        r = (bin_num == "1" for octet_num in bitmap for bin_num in f"{octet_num:08b}")
        return ((numer + 1) + (table * 1024) for numer, bit in enumerate(r) if bit)

    # def detach_vlans_from_port(self, vlan_list: Vlans, port: int, request):
    #     return self._set_trunk_vlans_on_port(
    #         vlan_list=vlan_list,
    #         port_num=port,
    #         config_mode=config_mode,
    #         request=request
    #     )


SwitchDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, EltexSwitch)
