from typing import Optional, AnyStr, List
import struct

from netaddr import EUI
from django.utils.translation import gettext_lazy as _, gettext
from djing2.lib import safe_int, RuTimedelta
from ..base import (
    Vlans, Vlan, Macs, MacItem, BaseSwitchInterface, BasePortInterface,
    DeviceImplementationError
)
from ..utils import plain_ip_device_mon_template


class DLinkPort(BasePortInterface):
    pass


class DlinkDGS_3120_24SC_Telnet(BaseSwitchInterface):
    """Dlink DGS-3120-24SC"""
    has_attachable_to_customer = False
    tech_code = 'dlink_sw'
    description = _('DLink switch')
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

    # def login(self, login: str, password: str, *args, **kwargs) -> bool:
    #     return super().login(
    #         login_prompt=b'UserName:',
    #         login=login,
    #         password_prompt=b'PassWord:',
    #         password=password
    #     )

    # def _disable_prompt(self) -> None:
    #     self.write('disable clipaging')
    #     self.read_until(self.prompt)

    def read_port_vlan_info(self, port: int) -> Vlans:
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        vids = self.get_list_keyval('.1.3.6.1.4.1.171.10.134.1.1.10.3.4.1.1')
        for vid, vid2 in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            member_ports = self.get_item('.1.3.6.1.2.1.17.7.1.4.3.1.2.%d' % vid)
            if member_ports is None:
                return
            member_ports = self._make_ports_map(member_ports.encode()[:4])
            if not member_ports[port-1]:
                # if port num is not <port>
                continue
            name = self._get_vid_name(vid)
            yield Vlan(vid=vid, name=name)

    @staticmethod
    def _make_ports_map(data: AnyStr) -> List[bool]:
        if isinstance(data, str):
            data = data.encode()[:4]
        elif isinstance(data, bytes):
            data = data[:4]
        else:
            raise TypeError('data must be instance of bytes or str')
        i = int.from_bytes(data, 'big')
        return list(v == '1' for v in f'{i:032b}')

    def read_all_vlan_info(self) -> Vlans:
        vids = self.get_list_keyval('.1.3.6.1.4.1.171.10.134.1.1.10.3.4.1.1')
        for vid, vid2 in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            name = self._get_vid_name(vid)
            yield Vlan(vid=vid, name=name)

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
            vname = self._normalize_name(v.name)
            return self.set_multiple([
                ('1.3.6.1.2.1.17.7.1.4.3.1.5.%d' % v.vid, 4, 'i'),      # 4 - vlan со всеми функциями
                ('1.3.6.1.2.1.17.7.1.4.3.1.1.%d' % v.vid, vname, 'x'),  # имя влана
            ])

    def delete_vlans(self, vlan_list: Vlans) -> bool:
        req = [('1.3.6.1.2.1.17.7.1.4.3.1.5.%d' % v.vid, 6) for v in vlan_list]
        return self.set_multiple(req)

    def _toggle_vlan_on_port(self, vid: int, port: int, member: bool):
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        member_tagged = self.get_item('1.3.6.1.2.1.17.7.1.4.3.1.3.%d' % vid)
        if member_tagged is None:
            return False
        member_tagged_map = self._make_ports_map(member_tagged)
        member_tagged_map[port - 1] = member
        i = int(''.join('1' if m else '0' for m in member_tagged_map), base=2)
        return self.set(
            oid='1.3.6.1.2.1.17.7.1.4.3.1.2.%d' % vid,
            value=struct.pack('!I', i),
            snmp_type='x'
        )

    def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
        return self._toggle_vlan_on_port(vid=vid, port=port, member=True)

    def detach_vlan_from_port(self, vid: int, port: int) -> bool:
        return self._toggle_vlan_on_port(vid=vid, port=port, member=False)

    def get_ports(self) -> tuple:
        ifs_ids = self.get_list('.1.3.6.1.2.1.10.7.2.1.1')
        return tuple(self.get_port(snmp_num=if_id) for if_id in ifs_ids)

    def get_port(self, snmp_num: int):
        snmp_num = safe_int(snmp_num)
        status = self.get_item('.1.3.6.1.2.1.2.2.1.7.%d' % snmp_num)
        status = status and int(status) == 1
        return DLinkPort(
            num=snmp_num,
            name=self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % snmp_num),
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
