from typing import Optional

from devices.schemas import DeviceOnuConfigTemplateSchema

VlanList = list[int]
OptVlanList = Optional[VlanList]


def get_all_vlans_from_config(config: DeviceOnuConfigTemplateSchema) -> OptVlanList:
    # config = {
    #     'configTypeCode': 'zte_f660_bridge',
    #     'vlanConfig': [
    #         {
    #             'port': 1,
    #             'vids': [
    #                 {'vid': 151, 'native': True}
    #             ]
    #         },
    #         {
    #             'port': 2,
    #             'vids': [
    #                 {'vid': 263, 'native': False},
    #                 {'vid': 264, 'native': False},
    #                 {'vid': 265, 'native': False},
    #             ]
    #         }
    #     ]
    # }
    vlan_config = config.vlanConfig
    if not vlan_config:
        return None
    all_vlan_ports = (v.vids for v in vlan_config)
    # all_vlan_ports = [
    #     [
    #         {'vid': 151, 'native': True}
    #     ],
    #     [
    #         {'vid': 263, 'native': False},
    #         {'vid': 264, 'native': False},
    #         {'vid': 265, 'native': False}
    #     ]
    # ]
    all_vids = {x.vid for b in all_vlan_ports if b for x in b}
    return [v for v in all_vids if v]
