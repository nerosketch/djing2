from .dgs_3120_24sc import DlinkDGS_3120_24SCSwitchInterface


class DlinkDGS_3627GSwitchInterface(DlinkDGS_3120_24SCSwitchInterface):
    """Dlink DGS-3627G"""

    has_attachable_to_customer = True
    tech_code = "dlink_sw"
    description = "DLink DGS-3627G"
    is_use_device_port = True
    ports_len = 24
