from devices.device_config.base import ListDeviceConfigType
from .onu_zte_f660 import OnuZTE_F660


class OnuZTE_F601(OnuZTE_F660):
    description = 'Zte ONU F601'
    ports_len = 1

    @staticmethod
    def get_config_types() -> ListDeviceConfigType:
        from .onu_config.zte_f601_bridge_config import ZteF601BridgeScriptModule
        return [ZteF601BridgeScriptModule]

    def default_vlan_info(self):
        default_vid = 1
        if self.dev_instance and self.dev_instance.parent_dev and self.dev_instance.parent_dev.extra_data:
            default_vid = self.dev_instance.parent_dev.extra_data.get('default_vid', 1)
        return [
            {
                'port': 1,
                'vids': [{'vid': default_vid, 'native': True}]
            }
        ]
