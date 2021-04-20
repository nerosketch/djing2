import math
from typing import Optional, Generator, Iterable, Dict

from django.utils.translation import gettext_lazy as _

from djing2.lib import safe_int, RuTimedelta, process_lock
from devices.device_config.base import (
    BasePortInterface,
    Vlans,
    Vlan,
    MacItem,
    Macs,
    DeviceImplementationError,
)
from devices.device_config.utils import plain_ip_device_mon_template
from ..dlink import DlinkDGS1100_10ME


class EltexPort(BasePortInterface):
    def get_config_types(self):
        return []


class EltexSwitch(DlinkDGS1100_10ME):
    description = _("Eltex switch")
    is_use_device_port = False
    has_attachable_to_customer = True
    tech_code = "eltex_sw"
    ports_len = 24

    def get_ports(self) -> tuple:
        def build_port(s, i: int, n: int):
            speed = self.get_item(".1.3.6.1.2.1.2.2.1.5.%d" % n)
            return EltexPort(
                s,
                num=i,
                name=self.get_item(".1.3.6.1.2.1.31.1.1.1.18.%d" % n),
                status=self.get_item(".1.3.6.1.2.1.2.2.1.7.%d" % n) == 1,
                mac=self.get_item(".1.3.6.1.2.1.2.2.1.6.%d" % n),
                uptime=self.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % n),
                speed=int(speed or 0),
            )

        return tuple(build_port(self, i, n) for i, n in enumerate(range(49, self.ports_len + 49), 1))

    def get_device_name(self):
        return self.get_item(".1.3.6.1.2.1.1.5.0")

    def get_uptime(self):
        uptimestamp = safe_int(self.get_item(".1.3.6.1.2.1.1.3.0"))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return tm

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.dev_instance
        return plain_ip_device_mon_template(device)

    def save_config(self) -> bool:
        return self.set_multiple(
            [
                ("1.3.6.1.4.1.89.87.2.1.3.1", 1, "i"),
                ("1.3.6.1.4.1.89.87.2.1.7.1", 2, "i"),
                ("1.3.6.1.4.1.89.87.2.1.8.1", 1, "i"),
                ("1.3.6.1.4.1.89.87.2.1.12.1", 3, "i"),
                ("1.3.6.1.4.1.89.87.2.1.17.1", 4, "i"),
            ]
        )

    def reboot(self, save_before_reboot=False) -> bool:
        if save_before_reboot:
            if not self.save_config():
                return False
            if not self.set("1.3.6.1.4.1.89.1.10.0", 8, snmp_type="t"):
                return False
        else:
            if not self.set("1.3.6.1.4.1.89.1.10.0", 0, snmp_type="t"):
                return False
        return True

    def port_disable(self, port_num: int):
        self.set_int_value("%s.%d" % (".1.3.6.1.2.1.2.2.1.7", port_num + 48), 2)

    def port_enable(self, port_num: int):
        self.set_int_value("%s.%d" % (".1.3.6.1.2.1.2.2.1.7", port_num + 48), 1)

    def read_port_vlan_info(self, port: int) -> Vlans:
        def _calc_ret(vlan_untagged_egress_oid, vlan_egress_bitmap, table_no) -> Vlans:
            vlan_untagged_egress = self.get_item(vlan_untagged_egress_oid)
            vlan_untagged_egress = list(self.parse_eltex_vlan_map(vlan_untagged_egress, table=table_no))
            is_native = next((v == 1 for i, v in enumerate(vlan_untagged_egress, 1) if i >= port), False)
            return (
                Vlan(vid=vid, title=self._get_vid_name(vid=vid), native=is_native)
                for vid in self.parse_eltex_vlan_map(vlan_egress_bitmap, table=table_no)
            )

        if port > self.ports_len or port < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)
        port = port + 48

        # rldot1qPortVlanStaticEgressList1to1024
        vlan_egress = self.get_item("1.3.6.1.4.1.89.48.68.1.1.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList1to1024
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.5.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=0,
            )

        # rldot1qPortVlanStaticEgressList1025to2048
        vlan_egress = self.get_item("1.3.6.1.4.1.89.48.68.1.2.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList1025to2048
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.6.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=1,
            )
        # rldot1qPortVlanStaticEgressList2049to3072
        vlan_egress = self.get_item("1.3.6.1.4.1.89.48.68.1.3.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList2049to3072
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.7.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=2,
            )
        # rldot1qPortVlanStaticEgressList3073to4094
        vlan_egress = self.get_item("1.3.6.1.4.1.89.48.68.1.4.%d" % port)
        if vlan_egress:
            return _calc_ret(
                # rldot1qPortVlanStaticUntaggedEgressList3073to4094
                vlan_untagged_egress_oid="1.3.6.1.4.1.89.48.68.1.8.%d" % port,
                vlan_egress_bitmap=vlan_egress,
                table_no=3,
            )

    def read_all_vlan_info(self) -> Vlans:
        snmp_vid = 100000
        while True:
            res = self.get_next(".1.3.6.1.2.1.2.2.1.1.%d" % snmp_vid)
            if res.snmp_type != "INTEGER":
                break
            vid = snmp_vid = safe_int(res.value)
            if vid < 100000 or vid > 104095:
                break
            vid = (vid - 100000) + 1
            name = self._get_vid_name(vid=vid)
            yield Vlan(vid=vid, title=name)

    @process_lock()
    def read_mac_address_port(self, port_num: int) -> Macs:
        if port_num > self.ports_len or port_num < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)
        try:
            ports_map = {int(i): n + 1 for n, i in enumerate(self.get_list(".1.3.6.1.2.1.2.2.1.1")) if int(i) > 0}
        except ValueError:
            return
        for fdb_port, oid in self.get_list_with_oid(".1.3.6.1.2.1.17.7.1.2.2.1.2"):
            real_fdb_port_num = ports_map.get(int(fdb_port))
            if port_num != real_fdb_port_num:
                continue
            vid = safe_int(oid[-7:-6][0])
            fdb_mac = ":".join("%.2x" % int(i) for i in oid[-6:])
            vid_name = self._get_vid_name(vid)
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=real_fdb_port_num)

    def read_mac_address_vlan(self, vid: int) -> Macs:
        try:
            ports_map = {int(i): n + 1 for n, i in enumerate(self.get_list(".1.3.6.1.2.1.2.2.1.1")) if int(i) > 0}
        except ValueError:
            return
        for fdb_port, oid in self.get_list_with_oid(".1.3.6.1.2.1.17.7.1.2.2.1.2.%d" % vid):
            real_fdb_port_num = ports_map.get(int(fdb_port))
            fdb_mac = ":".join("%.2x" % int(i) for i in oid[-6:])
            vid_name = self._get_vid_name(vid)
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=real_fdb_port_num)

    def create_vlans(self, vlan_list: Vlans) -> bool:
        for vlan in vlan_list:
            oids = (
                ("1.3.6.1.2.1.17.7.1.4.3.1.1.%d" % vlan.vid, vlan.title, "s"),
                ("1.3.6.1.2.1.17.7.1.4.3.1.2.%d" % vlan.vid, 0, "x"),
                ("1.3.6.1.2.1.17.7.1.4.3.1.3.%d" % vlan.vid, 0, "x"),
                ("1.3.6.1.2.1.17.7.1.4.3.1.4.%d" % vlan.vid, 0, "x"),
                ("1.3.6.1.2.1.17.7.1.4.3.1.5.%d" % vlan.vid, 4, "i"),
            )
            if not self.set_multiple(oid_values=oids):
                return False
        return True

    def delete_vlans(self, vlan_list: Vlans) -> bool:
        for vlan in vlan_list:
            if not self.set_int_value("1.3.6.1.2.1.17.7.1.4.3.1.5.%d" % vlan.vid, 6):
                return False
        return True

    @staticmethod
    def make_eltex_map_vlan(vids: Iterable[int]) -> Dict[int, bytes]:
        """
        https://eltexsl.ru/wp-content/uploads/2016/05/monitoring-i-upravlenie-ethernet-kommutatorami-mes-po-snmp.pdf
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
        vids = list(vids)
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
        https://eltexsl.ru/wp-content/uploads/2016/05/monitoring-i-upravlenie-ethernet-kommutatorami-mes-po-snmp.pdf
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
        assert isinstance(bitmap, bytes)
        if table < 0 or table > 3:
            raise DeviceImplementationError("table must be in range 1-3")
        r = (bin_num == "1" for octet_num in bitmap for bin_num in f"{octet_num:08b}")
        return ((numer + 1) + (table * 1024) for numer, bit in enumerate(r) if bit)

    def _set_vlans_on_port(self, vlan_list: Vlans, port_num: int):
        if port_num > self.ports_len or port_num < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)
        port_num = port_num + 48
        vids = (v.vid for v in vlan_list)
        bit_maps = self.make_eltex_map_vlan(vids=vids)
        oids = []
        for tbl_num, bitmap in bit_maps.items():
            oids.append(("1.3.6.1.4.1.89.48.68.1.%d.%d" % (tbl_num, port_num), bitmap, "x"))
        return self.set_multiple(oids)

    def attach_vlans_to_port(self, vlan_list: Vlans, port_num: int) -> bool:
        return self._set_vlans_on_port(vlan_list=vlan_list, port_num=port_num)

    def detach_vlans_from_port(self, vlan_list: Vlans, port: int) -> bool:
        return self._set_vlans_on_port(vlan_list=vlan_list, port_num=port)

    def detach_vlan_from_port(self, vlan: Vlan, port: int) -> bool:
        _vlan_gen = (v for v in (vlan,))
        return self.detach_vlans_from_port(_vlan_gen, port)
