from typing import Optional, AnyStr, List, Generator
import struct

from netaddr import EUI
from django.utils.translation import gettext
from djing2.lib import safe_int, RuTimedelta
from ..base import (
    Vlans, Vlan, Macs, MacItem, BaseSwitchInterface, BasePortInterface,
    DeviceImplementationError
)
from ..utils import plain_ip_device_mon_template


class DLinkPort(BasePortInterface):
    pass


class DlinkDGS_3120_24SCSwitchInterface(BaseSwitchInterface):
    """Dlink DGS-3120-24SC"""
    has_attachable_to_customer = False
    tech_code = 'dlink_sw'
    description = 'DLink DGS-3120-24SC'
    is_use_device_port = True
    ports_len = 24

    def __init__(self, dev_instance, *args, **kwargs):
        if not dev_instance.ip_address:
            raise DeviceImplementationError(gettext('Ip address required'))
        dev_ip_addr = dev_instance.ip_address
        super().__init__(
            dev_instance=dev_instance, host=dev_ip_addr,
            snmp_community=str(dev_instance.man_passw)
        )

    def read_port_vlan_info(self, port: int) -> Vlans:
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        vid = 1
        while True:
            member_ports, vid = self.get_next_keyval('.1.3.6.1.2.1.17.7.1.4.3.1.2.%d' % vid)
            if not member_ports:
                break
            vid = safe_int(vid)
            if vid in (0, 1):
                break
            member_ports = self._make_ports_map(member_ports[:4])
            if not member_ports[port-1]:
                continue
            untagged_members = self.get_item('1.3.6.1.2.1.17.7.1.4.3.1.4.%d' % vid)
            untagged_members = self._make_ports_map(untagged_members[:4])
            name = self._get_vid_name(vid)
            yield Vlan(
                vid=vid,
                title=name,
                native=untagged_members[port-1]
            )

    @staticmethod
    def _make_ports_map(data: AnyStr) -> List[bool]:
        if isinstance(data, bytes):
            data = data[:4]
        else:
            raise TypeError('data must be instance of bytes, %s got instead' % data.__class__)
        i = int.from_bytes(data, 'big')
        return list(v == '1' for v in f'{i:032b}')

    @staticmethod
    def _make_buf_from_ports_map(ports_map: List) -> bytes:
        i = int(''.join('1' if m else '0' for m in ports_map), base=2)
        return struct.pack('!I', i)

    def read_all_vlan_info(self) -> Vlans:
        vids = self.get_list_keyval('.1.3.6.1.2.1.17.7.1.4.3.1.1')
        for vid_name, vid in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            yield Vlan(vid=vid, title=vid_name)

    def read_mac_address_port(self, port_num: int) -> Macs:
        if port_num > self.ports_len or port_num < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        fdb = self.get_list_with_oid('.1.3.6.1.2.1.17.7.1.2.2.1.2')
        for fdb_port, oid in fdb:
            if port_num != int(fdb_port):
                continue
            vid = safe_int(oid[-7:-6][0])
            fdb_mac = str(EUI(':'.join('%.2x' % int(i) for i in oid[-6:])))
            vid_name = self._get_vid_name(vid)
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=safe_int(port_num))

    def read_mac_address_vlan(self, vid: int) -> Macs:
        vid = safe_int(vid)
        if vid > 4095 or vid < 1:
            raise ValueError('VID must be in range 1-%d' % 4095)
        fdb = self.get_list_with_oid('.1.3.6.1.2.1.17.7.1.2.2.1.2.%d' % vid)
        vid_name = self._get_vid_name(vid)
        for port_num, oid in fdb:
            fdb_mac = str(EUI(':'.join('%.2x' % int(i) for i in oid[-6:])))
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=safe_int(port_num))

    def create_vlans(self, vlan_list: Vlans) -> bool:
        # ('1.3.6.1.2.1.17.7.1.4.3.1.3.152', b'\xff\xff\xff\xff', 'OCTETSTR'),  # untagged порты
        for v in vlan_list:
            vname = self._normalize_name(v.title)
            return self.set_multiple([
                ('1.3.6.1.2.1.17.7.1.4.3.1.5.%d' % v.vid, 4, 'i'),      # 4 - vlan со всеми функциями
                ('1.3.6.1.2.1.17.7.1.4.3.1.1.%d' % v.vid, vname, 'x'),  # имя влана
            ])

    def delete_vlans(self, vlan_list: Vlans) -> bool:
        req = [('1.3.6.1.2.1.17.7.1.4.3.1.5.%d' % v.vid, 6) for v in vlan_list]
        return self.set_multiple(req)

    def _toggle_vlan_on_port(self, vlan: Vlan, port: int, member: bool):
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        port_member_tagged = self.get_item('.1.3.6.1.2.1.17.7.1.4.3.1.3.%d' % vlan.vid)
        port_member_untag = self.get_item('.1.3.6.1.2.1.17.7.1.4.3.1.2.%d' % vlan.vid)
        print('port_member_tagged:', vlan.vid, port_member_tagged)
        print('port_member_untag:', vlan.vid, port_member_untag)
        if port_member_tagged is None:
            return False
        port_member_tagged_map = self._make_ports_map(port_member_tagged)
        port_member_tagged_map[port - 1] = member

        buf = self._make_buf_from_ports_map(port_member_tagged_map).decode()
        return True

        if vlan.native:
            return self.set_multiple(oid_values=[
                ('.1.3.6.1.2.1.17.7.1.4.3.1.3.%d' % vlan.vid, buf, 'OCTETSTR'),
                ('.1.3.6.1.2.1.17.7.1.4.3.1.2.%d' % vlan.vid, buf, 'OCTETSTR')
            ])
        else:
            return self.set(
                oid='1.3.6.1.2.1.17.7.1.4.3.1.2.%d' % vlan.vid,
                value=buf,
                snmp_type='OCTETSTR'
            )

    def attach_vlans_to_port(self, vlan_list: Vlans, port_num: int) -> tuple:
        if port_num > self.ports_len or port_num < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)

        results = tuple(
            self._toggle_vlan_on_port(vlan=v, port=port_num, member=True)
            for v in vlan_list
        )
        return results

    def attach_vlan_to_port(self, vlan: Vlan, port: int, tag: bool = True) -> bool:
        return self._toggle_vlan_on_port(vlan=vlan, port=port, member=True)

    def detach_vlan_from_port(self, vlan: Vlan, port: int) -> bool:
        return self._toggle_vlan_on_port(vlan=vlan, port=port, member=False)

    def get_ports(self) -> Generator:
        ifs_ids = self.get_list('.1.3.6.1.2.1.10.7.2.1.1')
        return (self.get_port(snmp_num=if_id) for if_id in ifs_ids)

    def get_port(self, snmp_num: int):
        snmp_num = safe_int(snmp_num)
        status = self.get_item('.1.3.6.1.2.1.2.2.1.7.%d' % snmp_num)
        status = status and int(status) == 1
        return DLinkPort(
            num=snmp_num,
            name=self.get_item('.1.3.6.1.2.1.31.1.1.1.18.%d' % snmp_num),
            status=status,
            mac=self.get_item('.1.3.6.1.2.1.2.2.1.6.%d' % snmp_num),
            speed=self.get_item('.1.3.6.1.2.1.2.2.1.5.%d' % snmp_num),
            uptime=self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % snmp_num),
            dev_interface=self
        )

    def port_disable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num), 2
        )

    def port_enable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num), 1
        )

    def get_device_name(self):
        return self.get_item('.1.3.6.1.2.1.1.1.0')

    def get_uptime(self) -> str:
        uptimestamp = safe_int(self.get_item('.1.3.6.1.2.1.1.8.0'))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return str(tm)

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # Dlink has no require snmp info
        pass

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.dev_instance
        return plain_ip_device_mon_template(device)

    def register_device(self, extra_data: dict):
        pass
