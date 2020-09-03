import re
from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from devices.device_config import expect_util
from devices.device_config.base import DeviceConfigType, OptionalScriptCallResult, DeviceConfigurationError
from devices.device_config.expect_util import ExpectValidationError
from djing2.lib import process_lock
from .. import zte_utils


VlanList = List[int]


def _get_onu_template(vlans: VlanList) -> tuple:
    vids = ','.join(map(str, vlans))
    return (
        'sn-bind enable sn',
        'tcont 1 profile HSI_100',
        'gemport 1 unicast tcont 1 dir both',
        'security storm-control broadcast rate 8 direction egress vport 1',
        'security storm-control broadcast rate 8 direction ingress vport 1',
        'switchport mode trunk vport 1',
        f'switchport vlan {vids} tag vport 1'
    )


def _get_onu_mng_template(vlans: VlanList, config: dict):
    all_vids = ','.join(map(str, set(vlans)))
    vlan_config = config.get('vlanConfig')

    ports_config = []

    for port_conf in vlan_config:
        port_num = port_conf.get('port')

        vids = port_conf.get('vids')
        if not vids:
            continue

        native_vids = (vid.get('vid') for vid in vids if vid.get('native', False))
        native_vids = list(set(native_vids))
        trunk_vids = (vid.get('vid') for vid in vids if not vid.get('native', False))
        trunk_vids = list(set(trunk_vids))

        native_vids_len = len(native_vids)
        trunk_vids_len = len(trunk_vids)

        if native_vids_len > 1:
            raise expect_util.ExpectValidationError(_('Multiple native vid is not allowed on one port'))

        if native_vids_len == 1:
            if trunk_vids_len > 0:
                # Trunk with access port, Hybrid
                ports_config.extend([
                    'vlan port eth_0/%d mode hybrid def-vlan %d' % (port_num, native_vids[0]),
                    'vlan port eth_0/%d vlan %s' % (port_num, ','.join(map(str, trunk_vids)))
                ])
            elif trunk_vids_len == 0:
                # Only Access port
                ports_config.append('vlan port eth_0/%d mode tag vlan %d' % (port_num, native_vids[0]))
        elif native_vids_len == 0:
            if trunk_vids_len > 0:
                # Only trunk port
                ports_config.extend([
                    'vlan port eth_0/%d mode trunk' % port_num,
                    'vlan port eth_0/%d vlan %s' % (port_num, ','.join(map(str, trunk_vids)))
                ])
            elif trunk_vids_len == 0:
                # Without vlan config, type default vlan
                ports_config.append('vlan port eth_0/%d mode tag vlan 1' % port_num)

    return [
        f'service HSI type internet gemport 1 vlan {all_vids}',
        'loop-detect ethuni eth_0/1 enable',
        'loop-detect ethuni eth_0/2 enable',
        'loop-detect ethuni eth_0/3 enable',
        'loop-detect ethuni eth_0/4 enable',
        'interface pots pots_0/1 state lock',
        'interface pots pots_0/2 state lock',
        'interface wifi wifi_0/1 state lock'
    ] + ports_config + [
        # 'vlan port eth_0/1 mode tag vlan 123',
        # 'vlan port eth_0/2 mode tag vlan 123',
        # 'vlan port eth_0/3 mode tag vlan 123',
        # 'vlan port eth_0/4 mode tag vlan 123',
        'dhcp-ip ethuni eth_0/1 forbidden',
        'dhcp-ip ethuni eth_0/2 forbidden',
        'dhcp-ip ethuni eth_0/3 forbidden',
        'dhcp-ip ethuni eth_0/4 forbidden'
    ]


def _get_all_vlans_from_config(config: dict) -> Optional[VlanList]:
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
    vlan_config = config.get('vlanConfig')
    if not vlan_config:
        return None
    all_vlan_ports = (v.get('vids') for v in vlan_config)
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
    all_vids = set(x.get('vid') for b in all_vlan_ports if b for x in b)
    return [v for v in all_vids if v]


@process_lock(lock_name='zte_olt')
def _zte_onu_bridge_config_apply(serial: str, zte_ip_addr: str, telnet_login: str,
                                 telnet_passw: str, telnet_prompt: str, config: dict,
                                 *args, **kwargs):
    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise expect_util.ExpectValidationError('ip address for zte not valid')

    if not re.match(r'^ZTEG[0-9A-F]{8}$', serial):
        raise ExpectValidationError('Serial not valid, match: ^ZTEG[0-9A-F]{8}$')

    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise ExpectValidationError('ip address for zte not valid')

    all_vids = _get_all_vlans_from_config(config=config)
    if not all_vids:
        raise zte_utils.OnuZteRegisterError(f'not passed vlan list')

    # Enter via telnet
    ch = expect_util.MySpawn('telnet %s' % zte_ip_addr)
    ch.timeout = 15
    ch.expect_exact('Username:')
    ch.do_cmd(telnet_login, 'Password:')

    choice = ch.do_cmd(telnet_passw, ['bad password.', f'{telnet_prompt}#'])
    if choice == 0:
        raise zte_utils.ZteOltLoginFailed

    ch.do_cmd('terminal length 0', f'{telnet_prompt}#')

    # Find unregistered onu ↓
    choice = ch.do_cmd('show gpon onu uncfg', [
        'No related information to show',
        f'{telnet_prompt}#'
    ])
    if choice == 0:
        ch.close()
        raise zte_utils.OnuZteRegisterError(f'unregistered onu not found, sn={serial}')
    if choice == 1:
        # get unregistered onu devices
        unregistered_onu = zte_utils.get_unregistered_onu(
            lines=ch.get_lines_before(),
            serial=serial
        )
        if unregistered_onu is None:
            ch.close()
            raise zte_utils.OnuZteRegisterError(f'unregistered onu not found, sn={serial}')

        stack_num = int(unregistered_onu.get('stack_num'))
        rack_num = int(unregistered_onu.get('rack_num'))
        fiber_num = int(unregistered_onu.get('fiber_num'))

        # get last registered onu
        ch.do_cmd(f'show run int gpon-olt_{stack_num}/{rack_num}/{fiber_num}',
                  f'{telnet_prompt}#')
        free_onu_number = zte_utils.get_free_registered_onu_number(
            ch.get_lines_before()
        )
        if free_onu_number > 127:
            ch.close()
            raise zte_utils.ZTEFiberIsFull(f'olt fiber {fiber_num} is full')

        # enter to config
        ch.do_cmd('conf t', f'{telnet_prompt}(config)#')

        config_if_prompt = f'{telnet_prompt}(config-if)#'

        # go to olt interface
        ch.do_cmd(f'interface gpon-olt_1/{rack_num}/{fiber_num}', config_if_prompt)

        # register onu on olt interface
        ch.do_cmd(
            f'onu {free_onu_number} type ZTE-F660 sn {serial}',
            config_if_prompt
        )

        # Exit from int olt
        ch.do_cmd('exit', f'{telnet_prompt}(config)#')

        # Enter to int onu
        ch.do_cmd(
            f'int gpon-onu_1/{rack_num}/{fiber_num}:{free_onu_number}',
            config_if_prompt
        )

        # Apply int onu config
        template = _get_onu_template(vlans=all_vids)
        for line in template:
            ch.do_cmd(line, config_if_prompt)

        # Exit from int olt
        ch.do_cmd('exit', f'{telnet_prompt}(config)#')

        # Enter to pon-onu-mng
        ch.do_cmd(
            f'pon-onu-mng gpon-onu_1/{rack_num}/{fiber_num}:{free_onu_number}',
            f'{telnet_prompt}(gpon-onu-mng)#'
        )

        # Apply mng onu template
        template = _get_onu_mng_template(vlans=all_vids, config=config)
        mng_prompt = f'{telnet_prompt}(gpon-onu-mng)#'
        for line in template:
            ch.do_cmd(line, mng_prompt)

        # Exit
        ch.do_cmd('exit', f'{telnet_prompt}(config)#')
        ch.do_cmd('exit', f'{telnet_prompt}#')
        ch.close()
        return zte_utils.zte_onu_conv_to_num(
            rack_num=rack_num,
            fiber_num=fiber_num,
            port_num=free_onu_number
        )


class ZteF660BridgeStaticScriptModule(DeviceConfigType):
    title = 'Zte ONU F660 Static Bridge'
    short_code = 'zte_f660_bridge'
    accept_vlan = True

    @classmethod
    def entry_point(cls, config: dict, device, *args, **kwargs) -> OptionalScriptCallResult:
        pdev = device.parent_dev
        if not pdev:
            raise DeviceConfigurationError(_('You should config parent OLT device for ONU'))
        if not pdev.extra_data:
            raise DeviceConfigurationError(_('You have not info in extra_data '
                                             'field, please fill it in JSON'))
        zte_utils.reg_dev_zte(
            device=device,
            extra_data=dict(pdev.extra_data),
            reg_func=_zte_onu_bridge_config_apply,
            config=config
        )
        return {1: 'success'}
