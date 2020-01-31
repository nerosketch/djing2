from devices.switch_config import Vlans, Vlan
from djing2.lib import safe_int
from .dgs_3120_24sc import DlinkDGS_3120_24SCSwitchInterface


class DlinkDGS_1100_06MESwitchInterface(DlinkDGS_3120_24SCSwitchInterface):
    """Dlink DGS-1100-06/ME"""
    description = 'DLink DGS-1100-06/ME'
    ports_len = 6

    def read_all_vlan_info(self) -> Vlans:
        vids = self.get_list_keyval('.1.3.6.1.4.1.171.10.134.1.1.7.6.1.1')
        for vid_name, vid in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            yield Vlan(vid=vid, title=vid_name)

    # def login(self, login: str, password: str, *args, **kwargs) -> bool:
    #     return super().login(
    #                          login_prompt=b'UserName:',
    #                          login=login,
    #                          password_prompt=b'Password:',
    #                          password=password
    #                          )

    # def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
    #     if port > self.ports_len or port < 1:
    #         raise ValueError('Port must be in range 1-%d' % self.ports_len)
    #     tag_mark = 'tagged' if tag else 'untagged'
    #     self.write('config vlan vlanid %(vid)d add %(tag_mark)s %(port)d' % {
    #         'vid': vid,
    #         'port': port,
    #         'tag_mark': tag_mark
    #     })
    #     out = self.read_until(self.prompt)
    #     return b'Success' in out

    # def detach_vlan_from_port(self, vid: int, port: int) -> bool:
    #     if port > self.ports_len or port < 1:
    #         raise ValueError('Port must be in range 1-%d' % self.ports_len)
    #     self.write('config vlan vlanid %(vid)d delete %(port)d' % {
    #         'vid': vid,
    #         'port': port
    #     })
    #     out = self.read_until(self.prompt)
    #     return b'Success' in out
