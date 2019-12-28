from netaddr import EUI

from djing2.lib import safe_int
from ..base import Vlans, Vlan, Macs, MacItem
from .dgs_3120_24sc import DlinkDGS_3120_24SC_Telnet


class DlinkDGS_1100_06ME_Telnet(DlinkDGS_3120_24SC_Telnet):
    """Dlink DGS-1100-06/ME"""
    ports_len = 6

    def __init__(self, prompt: bytes = None, *args, **kwargs):
        super().__init__(
            prompt=prompt or b'DGS-1100-06/ME:5#',
            *args, **kwargs
        )

    def login(self, login: str, password: str, *args, **kwargs) -> bool:
        return super().login(
                             login_prompt=b'UserName:',
                             login=login,
                             password_prompt=b'Password:',
                             password=password
                             )

    def read_port_vlan_info(self, port: int) -> Vlans:
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        self.write('show vlan ports %d' % port)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) == 3:
                try:
                    vid = int(chunks[0])
                    yield Vlan(vid, '')
                except ValueError:
                    pass

    def read_mac_address_port(self, port_num: int) -> Macs:
        if port_num > self.ports_len or port_num < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        self.write('show fdb port %d' % port_num)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) != 5:
                continue
            try:
                vid = int(chunks[0])
                vname = chunks[1]
                mac = EUI(chunks[2].decode())
                port = chunks[3].decode()
                yield MacItem(vid=vid, name=vname.decode(), mac=mac, port=safe_int(port))
            except (ValueError, IndexError):
                pass

    def read_mac_address_vlan(self, vid: int) -> Macs:
        self.write('show fdb vlanid %d' % vid)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) != 5:
                continue
            try:
                vlan_id = int(chunks[0])
                assert vid == vlan_id, 'Catch vid(%d) that is not equal to passed vid(%d)' % (
                    vlan_id, vid
                )
                vname = chunks[1].decode()
                mac = EUI(chunks[2].decode())
                port = chunks[3]
                yield MacItem(vid=vlan_id, name=vname, mac=mac, port=safe_int(port))
            except (ValueError, IndexError):
                pass

    def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        tag_mark = 'tagged' if tag else 'untagged'
        self.write('config vlan vlanid %(vid)d add %(tag_mark)s %(port)d' % {
            'vid': vid,
            'port': port,
            'tag_mark': tag_mark
        })
        out = self.read_until(self.prompt)
        return b'Success' in out

    def detach_vlan_from_port(self, vid: int, port: int) -> bool:
        if port > self.ports_len or port < 1:
            raise ValueError('Port must be in range 1-%d' % self.ports_len)
        self.write('config vlan vlanid %(vid)d delete %(port)d' % {
            'vid': vid,
            'port': port
        })
        out = self.read_until(self.prompt)
        return b'Success' in out
