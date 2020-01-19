import math
from typing import Optional, AnyStr, List

from netaddr import EUI
from django.utils.translation import gettext_lazy as _

from djing2.lib import safe_int, RuTimedelta
from ..base import BasePortInterface, Vlans, Vlan, MacItem, Macs
from ..utils import plain_ip_device_mon_template
from ..dlink import DlinkDGS1100_10ME


class EltexPort(BasePortInterface):
    pass


class EltexSwitch(DlinkDGS1100_10ME):
    description = _('Eltex switch')
    is_use_device_port = False
    has_attachable_to_customer = True
    tech_code = 'eltex_sw'
    ports_len = 26

    def get_ports(self) -> tuple:
        def build_port(s, i: int, n: int):
            speed = self.get_item('.1.3.6.1.2.1.2.2.1.5.%d' % n)
            return EltexPort(
                s,
                num=i,
                name=self.get_item('.1.3.6.1.2.1.31.1.1.1.18.%d' % n),
                status=self.get_item('.1.3.6.1.2.1.2.2.1.8.%d' % n),
                mac=self.get_item('.1.3.6.1.2.1.2.2.1.6.%d' % n),
                uptime=self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % n),
                speed=int(speed or 0)
            )

        return tuple(build_port(self, i, n) for i, n in enumerate(range(49, self.ports_len+50), 1))

    def get_device_name(self):
        return self.get_item('.1.3.6.1.2.1.1.5.0')

    def get_uptime(self):
        uptimestamp = safe_int(self.get_item('.1.3.6.1.2.1.1.3.0'))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return tm

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.dev_instance
        return plain_ip_device_mon_template(device)

    def save_config(self) -> bool:
        return self.set_multiple([
            ('1.3.6.1.4.1.89.87.2.1.3.1', 1, 'i'),
            ('1.3.6.1.4.1.89.87.2.1.7.1', 2, 'i'),
            ('1.3.6.1.4.1.89.87.2.1.8.1', 1, 'i'),
            ('1.3.6.1.4.1.89.87.2.1.12.1', 3, 'i'),
            ('1.3.6.1.4.1.89.87.2.1.17.1', 4, 'i')
        ])

    def reboot(self, save_before_reboot=False) -> bool:
        if save_before_reboot:
            if not self.save_config():
                return False
            if not self.set('1.3.6.1.4.1.89.1.10.0', 8, snmp_type='t'):
                return False
        else:
            if not self.set('1.3.6.1.4.1.89.1.10.0', 0, snmp_type='t'):
                return False
        return True

    def port_disable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num),
            2
        )

    def port_enable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num),
            1
        )

    def read_port_vlan_info(self, port: int) -> Vlans:
        self.write('show int switc gi1/0/%d' % port)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) != 4:
                continue
            vid = safe_int(chunks[0])
            if vid > 0:
                vname = chunks[1].decode()
                yield Vlan(vid=vid, name=vname)

    # def _disable_prompt(self):
    #     self.write('terminal datadump')
    #     self.read_until(self.prompt)

    # @staticmethod
    # def _port_parse(port_descr: str) -> int:
    #     if '/' in port_descr:
    #         gi, zero, port_num = port_descr.split('/')
    #         return safe_int(port_num)
    #     raise RuntimeError('port not match to "giN/N/N" where N is digit')

    def read_all_vlan_info(self) -> Vlans:
        snmp_vid = 100000
        while True:
            res = self.get_next('.1.3.6.1.2.1.2.2.1.1.%d' % snmp_vid)
            if res.snmp_type != 'INTEGER':
                break
            vid = snmp_vid = safe_int(res.value)
            if vid < 100000 or vid > 104095:
                break
            vid = (vid - 100000) + 1
            name = self._get_vid_name(vid=vid)
            yield Vlan(vid=vid, name=name)

    def read_mac_address_port(self, port_num: int) -> Macs:
        if port_num > self.ports_len or port_num < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        try:
            ports_map = {int(i): n+1 for n, i in enumerate(self.get_list('.1.3.6.1.2.1.2.2.1.1')) if int(i) > 0}
        except ValueError:
            return
        for fdb_port, oid in self.get_list_with_oid('.1.3.6.1.2.1.17.7.1.2.2.1.2'):
            real_fdb_port_num = ports_map.get(int(fdb_port))
            if port_num != real_fdb_port_num:
                continue
            vid = safe_int(oid[-7:-6][0])
            fdb_mac = str(EUI(':'.join('%.2x' % int(i) for i in oid[-6:])))
            vid_name = self._get_vid_name(vid)
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=real_fdb_port_num)

    def read_mac_address_vlan(self, vid: int) -> Macs:
        try:
            ports_map = {int(i): n+1 for n, i in enumerate(self.get_list('.1.3.6.1.2.1.2.2.1.1')) if int(i) > 0}
        except ValueError:
            return
        for fdb_port, oid in self.get_list_with_oid('.1.3.6.1.2.1.17.7.1.2.2.1.2.%d' % vid):
            real_fdb_port_num = ports_map.get(int(fdb_port))
            fdb_mac = str(EUI(':'.join('%.2x' % int(i) for i in oid[-6:])))
            vid_name = self._get_vid_name(vid)
            yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=real_fdb_port_num)

    def create_vlans(self, vlan_list: Vlans) -> bool:
        self.write('conf')
        self.read_until('(config)#')
        self.write('vlan database')
        self.read_until('(config-vlan)#')
        for vlan in vlan_list:
            self.write('vlan %(vid)d name %(name)s' % {
                'vid': vlan.vid,
                'name': self._normalize_name(vlan.name)
            })
            self.read_until('(config-vlan)#')
        self.write('exit')
        self.read_until('(config)#')
        self.write('exit')
        self.read_until(self.prompt)
        return True

    def delete_vlans(self, vlan_list: Vlans) -> bool:
        self.write('conf')
        self.read_until('(config)#')
        self.write('vlan database')
        self.read_until('(config-vlan)#')
        for vlan in vlan_list:
            self.write('no vlan %d' % vlan.vid)
            self.read_until('(config-vlan)#')
        self.write('exit')
        self.read_until('(config)#')
        self.write('exit')
        self.read_until(self.prompt)
        return True

    # @staticmethod
    # def make_single_map_vlan(vid: int) -> str:
    #     if vid > 4095 or vid < 1:
    #         raise ValueError('VID must be in range 1-%d' % 4095)
    #     field_no = int(math.ceil(vid / 4))
    #     b = [0, 0, 0, 0]
    #     b[(field_no * 4) - vid - 1] = 1
    #     i = int(''.join(str(k) for k in b), base=2)
    #     bit_map = '0' * (field_no - 1)
    #     bit_map += str(i)
    #     return bit_map

    @staticmethod
    def _make_eltex_map_vlan(vid: int) -> str:
        """
        https://eltexsl.ru/wp-content/uploads/2016/05/monitoring-i-upravlenie-ethernet-kommutatorami-mes-po-snmp.pdf
        :param vid:
        :return: str bit map vlan representation by Eltex version
        >>> EltexSwitch._make_eltex_map_vlan(3100)
        '0000001'
        >>> EltexSwitch._make_eltex_map_vlan(622)
        '000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004'
        """
        if vid > 4095 or vid < 1:
            raise ValueError('VID must be in range 1-%d' % 4095)
        table_no = int(math.floor(vid / 1024))
        field_no = int(math.ceil(vid / 4)) - 1
        field_no = (field_no - 256 * table_no)
        b = [0, 0, 0, 0]
        if table_no > 0:
            field_index = int(vid / (256 * table_no)) - 1
        else:
            field_index = (field_no * 4) - vid - 1
        b[field_index] = 1
        i = int(''.join(str(k) for k in b), base=2)
        bit_map = '0' * field_no
        bit_map += str(i)
        return bit_map

    def attach_vlans_to_port(self, vlan_list: Vlans, port_num: int) -> bool:
        oids = []
        port_num = port_num + 49
        for v in vlan_list:
            bit_map = self._make_eltex_map_vlan(vid=v.vid)
            oids.append((
                '1.3.6.1.4.1.89.48.68.1.1.%d' % port_num,
                bit_map.zfill(10),
                'x'
            ))
        return self.set_multiple(oids)

    def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, name=None),))
        return self.attach_vlans_to_port(_vlan_gen, port)

    def detach_vlans_from_port(self, vlan_list: Vlans, port: int, rm_all: bool = False) -> bool:
        self.write('conf')
        self.read_until('(config)#')
        self.write('int gi1/0/%d' % port)
        self.read_until('(config-if)#')
        if rm_all:
            self.write('switchport trunk allowed vlan remove all')
        else:
            for v in vlan_list:
                self.write('switchport trunk allowed vlan remove %d' % v.vid)
        self.write('exit')
        self.read_until('(config)#')
        self.write('exit')
        self.read_until(self.prompt)
        return True

    def detach_vlan_from_port(self, vid: int, port: int) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, name=None),))
        return self.detach_vlans_from_port(_vlan_gen, port)

    # def login(self, login: str, password: str, *args, **kwargs) -> bool:
    #     r = super().login(
    #         login_prompt=b'User Name:',
    #         login=login,
    #         password_prompt=b'Password:',
    #         password=password
    #     )
    #     self._disable_prompt()
    #     return r
