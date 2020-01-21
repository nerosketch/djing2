import os
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from djing2.lib import safe_int
from .dgs_1100_06me import DlinkDGS_1100_06MESwitchInterface
from ..base import DeviceConfigurationError, Vlans, Vlan


def _ex_expect(filename, params=()):
    base_dir = getattr(settings, 'BASE_DIR')
    if base_dir is not None:
        exec_file = os.path.join(base_dir, 'devices', 'expect_scripts', filename)
        if os.path.isfile(exec_file) and os.access(path=exec_file, mode=os.X_OK):
            params = ' '.join(str(p) for p in params)
            if params:
                return os.system('%s %s' % (exec_file, params))
            else:
                return os.system(exec_file)
        else:
            raise DeviceConfigurationError(_('File %(filename)s is not exists or not executable') % {
                'filename': exec_file
            })


class DlinkDGS1100_10ME(DlinkDGS_1100_06MESwitchInterface):
    """Dlink DGS-1100-10/ME"""
    has_attachable_to_customer = True
    tech_code = 'dlink_sw'
    description = 'DLink DGS-1100-10/ME'
    is_use_device_port = True
    ports_len = 10

    def __init__(self, prompt: bytes = None, *args, **kwargs):
        DlinkDGS_1100_06MESwitchInterface.__init__(
            self,
            prompt=prompt or b'DGS-1100-10/ME:5#',
            *args, **kwargs
        )

    def read_all_vlan_info(self) -> Vlans:
        vids = self.get_list_keyval('.1.3.6.1.4.1.171.10.134.2.1.7.6.1.2')
        for vid_name, vid in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            yield Vlan(vid=vid, name=vid_name)

    def reboot(self, save_before_reboot=False):
        dat = self.dev_instance.extra_data
        if dat is None:
            raise DeviceConfigurationError(
                _('You have not info in extra_data '
                  'field, please fill it in JSON')
            )
        login = dat.get('login')
        passw = dat.get('password')
        if login and passw:
            return _ex_expect('dlink_DGS1100_reboot.exp', (
                self.dev_instance.ip_address,
                login, passw,
                1 if save_before_reboot else 0
            )), None

    # def login(self, login: str, password: str, *args, **kwargs) -> bool:
    #     return BaseDeviceInterface.login(self,
    #                                      login_prompt=b'login: ',
    #                                      login=login,
    #                                      password_prompt=b'Password:',
    #                                      password=password
    #                                      )
