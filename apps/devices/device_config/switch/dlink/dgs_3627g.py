from .dgs_3120_24sc import DlinkDGS_3120_24SCSwitchInterface
from .. import SwitchDeviceStrategyContext

_DEVICE_UNIQUE_CODE = 11


class DlinkDGS_3627GSwitchInterface(DlinkDGS_3120_24SCSwitchInterface):
    """Dlink DGS-3627G"""

    has_attachable_to_customer = True
    tech_code = "dlink_sw"
    description = "DLink DGS-3627G"
    is_use_device_port = True
    ports_len = 24


SwitchDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, DlinkDGS_3627GSwitchInterface)
