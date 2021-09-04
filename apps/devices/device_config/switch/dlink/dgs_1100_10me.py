import os
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .dgs_3120_24sc import DlinkDGS_3120_24SCSwitchInterface
from devices.device_config.base import DeviceConfigurationError
from ..switch_device_strategy import SwitchDeviceStrategyContext

DEVICE_UNIQUE_CODE = 1


def _ex_expect(filename, params=()):
    base_dir = getattr(settings, "BASE_DIR")
    if base_dir is not None:
        exec_file = os.path.join(base_dir, "devices", "expect_scripts", filename)
        if os.path.isfile(exec_file) and os.access(path=exec_file, mode=os.X_OK):
            params = " ".join(str(p) for p in params)
            if params:
                return os.system(f"{exec_file} {params}")
            else:
                return os.system(exec_file)
        else:
            raise DeviceConfigurationError(
                _("File %(filename)s is not exists or not executable") % {"filename": exec_file}
            )


class DlinkDGS1100_10ME(DlinkDGS_3120_24SCSwitchInterface):
    """Dlink DGS-1100-10/ME"""

    has_attachable_to_customer = True
    tech_code = "dlink_sw"
    description = "DLink DGS-1100-10/ME"
    is_use_device_port = True
    ports_len = 10

    def reboot(self, save_before_reboot=False):
        dat = self.model_instance.extra_data
        if dat is None:
            raise DeviceConfigurationError(_("You have not info in extra_data field, please fill it in JSON"))
        login = dat.get("login")
        passw = dat.get("password")
        if login and passw:
            return (
                _ex_expect(
                    "dlink_DGS1100_reboot.exp",
                    (self.model_instance.ip_address, login, passw, 1 if save_before_reboot else 0),
                ),
                None,
            )


SwitchDeviceStrategyContext.add_device_type(DEVICE_UNIQUE_CODE, DlinkDGS1100_10ME)
