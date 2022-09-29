from typing import Optional

from devices.device_config.pon.epon.epon_bdcom_fora import DefaultVlanDC

from . import OnuZTE_F660
from ..pon_device_strategy import PonONUDeviceStrategyContext

DEVICE_UNIQUE_CODE = 14


class OnuFD511G(OnuZTE_F660):
    description = "XPON ONU FD511G"
    ports_len = 1

    @staticmethod
    def get_config_types():
        from .onu_config.fd511g_ipoe_bridge import FD511GOnuDeviceConfigType

        return [FD511GOnuDeviceConfigType]

    def default_vlan_info(self) -> list[DefaultVlanDC]:
        r = super(OnuFD511G, self).default_vlan_info()
        return [r[0]]

    def get_details(self, sn_prefix='HWTC', mac_prefix='54:43') -> Optional[dict]:
        return super().get_details(sn_prefix=sn_prefix, mac_prefix=mac_prefix)

    def remove_from_olt(self, extra_data: dict, sn_prefix='HWTC', **kwargs):
        return super().remove_from_olt(
            extra_data=extra_data,
            sn_prefix=sn_prefix,
            mac_prefix='54:43'
        )


PonONUDeviceStrategyContext.add_device_type(DEVICE_UNIQUE_CODE, OnuFD511G)
