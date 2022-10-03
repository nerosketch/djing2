from devices.device_config.base import Vlan
from devices.device_config.pon.epon.epon_bdcom_fora import DefaultVlanDC

from .onu_zte_f660 import OnuZTE_F660
from ..pon_device_strategy import PonONUDeviceStrategyContext

DEVICE_UNIQUE_CODE = 7


class OnuZTE_F601(OnuZTE_F660):
    description = "Zte ONU F601"
    ports_len = 1

    @staticmethod
    def get_config_types():
        from .onu_config.zte_f601_bridge_config import ZteF601BridgeScriptModule
        from .onu_config.zte_f601_static import ZteF601StaticScriptModule

        return [ZteF601BridgeScriptModule, ZteF601StaticScriptModule]

    def default_vlan_info(self) -> list[DefaultVlanDC]:
        default_vid = 1
        dev = self.model_instance
        if dev and dev.parent_dev and dev.parent_dev.extra_data:
            default_vid = dev.parent_dev.extra_data.get("default_vid", 1)
        return [DefaultVlanDC(port=1, vids=[
            Vlan(vid=default_vid, native=True)
        ])]

    def read_onu_vlan_info(self):
        r = super().read_onu_vlan_info()
        try:
            return [next(r)]
        except TypeError:
            return list(r)[:1]
        except StopIteration:
            return ()


PonONUDeviceStrategyContext.add_device_type(DEVICE_UNIQUE_CODE, OnuZTE_F601)
