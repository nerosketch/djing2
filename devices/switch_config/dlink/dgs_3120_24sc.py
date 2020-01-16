from typing import Optional

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

    def login(self, login: str, password: str, *args, **kwargs) -> bool:
        return super().login(
            login_prompt=b'UserName:',
            login=login,
            password_prompt=b'PassWord:',
            password=password
        )

    def _disable_prompt(self) -> None:
        self.write('disable clipaging')
        self.read_until(self.prompt)

    def read_port_vlan_info(self, port: int) -> Vlans:
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        vids = self.get_list_keyval('.1.3.6.1.4.1.171.10.134.1.1.10.3.4.1.1')
        for vid, vid2 in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            member_ports = self.get_item_port_member('.1.3.6.1.2.1.17.7.1.4.3.1.2.%d' % vid)
            if not self._get_bit(member_ports, port):
                # if port num is not <port>
                continue
            name = self._get_vid_name(vid)
            yield Vlan(vid=vid, name=name)

    @staticmethod
    def _get_bit(num: int, pos: int) -> bool:
        pos = 32 - pos
        return bool((num & (1 << pos)) >> pos)

    def _get_vid_name(self, vid: int) -> str:
        return self.get_item('.1.3.6.1.2.1.17.7.1.4.3.1.1.%d' % vid)

    def get_item_port_member(self, oid: str) -> int:
        r = self.get_item(oid)[:4]
        return int.from_bytes(r, "big")

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
        for v in vlan_list:
            vname = self._normalize_name(v.name)
            self.write('create vlan %s tag %d' % (vname, v.vid))
            out = self.read_until(self.prompt)
            if b'Success' not in out:
                return False
        return True

    def delete_vlans(self, vlan_list: Vlans) -> bool:
        for v in vlan_list:
            self.write('delete vlan vlanid %d' % v.vid)
            out = self.read_until(self.prompt)
            if b'Success' not in out:
                return False
        return True

    def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
        tag_mark = 'tagged' if tag else 'untagged'
        self.write('config vlan vlanid %(vid)d add %(tag_mark)s 1:%(port)d' % {
            'vid': vid,
            'port': port,
            'tag_mark': tag_mark
        })
        out = self.read_until(self.prompt)
        return b'Success' in out

    def detach_vlan_from_port(self, vid: int, port: int) -> bool:
        self.write('config vlan vlanid %(vid)d delete 1:%(port)d' % {
            'vid': vid,
            'port': port
        })
        out = self.read_until(self.prompt)
        return b'Success' in out

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
