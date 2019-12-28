from typing import Optional

from netaddr import EUI
from django.utils.translation import gettext_lazy as _
from djing2.lib import safe_int, RuTimedelta
from ..base import Vlans, Vlan, Macs, MacItem, DevBase, BasePort, GeneratorOrTuple, SNMPBaseWorker
from ..utils import plain_ip_device_mon_template


class DLinkPort(BasePort):
    def __init__(self, snmp_worker, *args, **kwargs):
        super().__init__(writable=True, *args, **kwargs)
        if not issubclass(snmp_worker.__class__, SNMPBaseWorker):
            raise TypeError
        self.snmp_worker = snmp_worker


class DlinkDGS_3120_24SC_Telnet(DevBase):
    """Dlink DGS-3120-24SC"""
    has_attachable_to_customer = False
    tech_code = 'dlink_sw'
    description = _('DLink switch')
    is_use_device_port = True
    ports_len = 10

    def __init__(self, prompt: bytes = None, *args, **kwargs):
        super().__init__(
            prompt=prompt or b'DGS-3120-24SC:admin#',
            *args, **kwargs
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
        self.write('show vlan ports 1:%d' % port)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) > 2:
                port, vid = chunks[:2]
                yield Vlan(safe_int(vid), '')

    def read_all_vlan_info(self) -> Vlans:
        self.write('show vlan')
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            if b'VID' in line:
                chunks = line.split()
                if len(chunks) == 7:
                    vid = safe_int(chunks[2])
                    vname = chunks[6].decode()
                    yield Vlan(vid, vname)

    def read_mac_address_port(self, port_num: int) -> Macs:
        self.write('show fdb port 1:%d' % port_num)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) != 6:
                continue
            try:
                vid = int(chunks[0])
                vname = chunks[1]
                mac = EUI(chunks[2].decode())
                stack_num, port = chunks[3].split(b':')
                yield MacItem(vid=vid, name=vname.decode(), mac=mac, port=safe_int(port))
            except (ValueError, IndexError):
                pass

    def read_mac_address_vlan(self, vid: int) -> Macs:
        self.write('show fdb vlanid %d' % vid)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) != 6:
                continue
            try:
                vlan_id = int(chunks[0])
                assert vid == vlan_id, 'Catch vid(%d) that is not equal to passed vid(%d)' % (
                    vlan_id, vid
                )
                vname = chunks[1].decode()
                mac = EUI(chunks[2].decode())
                stack, port = chunks[3].split(b':')
                yield MacItem(vid=vlan_id, name=vname, mac=mac, port=safe_int(port))
            except (ValueError, IndexError):
                pass

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

    def get_ports(self) -> GeneratorOrTuple:
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
            snmp_worker=self
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

    def uptime(self) -> str:
        uptimestamp = safe_int(self.get_item('.1.3.6.1.2.1.1.8.0'))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return str(tm)

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # Dlink has no require snmp info
        pass

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.db_instance
        return plain_ip_device_mon_template(device)

    def register_device(self, extra_data: dict):
        pass
