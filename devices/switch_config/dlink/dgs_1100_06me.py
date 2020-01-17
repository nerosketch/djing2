# from netaddr import EUI

# from djing2.lib import safe_int
# from ..base import Macs, MacItem
from .dgs_3120_24sc import DlinkDGS_3120_24SC_Telnet


class DlinkDGS_1100_06ME_Telnet(DlinkDGS_3120_24SC_Telnet):
    """Dlink DGS-1100-06/ME"""
    ports_len = 6

    def __init__(self, prompt: bytes = None, *args, **kwargs):
        super().__init__(
            prompt=prompt or b'DGS-1100-06/ME:5#',
            *args, **kwargs
        )

    # def login(self, login: str, password: str, *args, **kwargs) -> bool:
    #     return super().login(
    #                          login_prompt=b'UserName:',
    #                          login=login,
    #                          password_prompt=b'Password:',
    #                          password=password
    #                          )

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
