import re

from django.utils.translation import gettext_lazy as _

from devices.device_config import expect_util
from devices.device_config.base import DeviceConfigType, OptionalScriptCallResult, DeviceConfigurationError
from devices.device_config.pon.gpon import zte_utils
from djing2.lib import process_lock


def _get_onu_template(vlan_id: int, mac_addr: str) -> tuple:
    return (
        'switchport mode hybrid vport 1',
        'service-port 1 vport 1 user-vlan %d vlan %d' % (vlan_id, vlan_id),
        'port-location format flexible-syntax vport 1',
        'port-location sub-option remote-id enable vport 1',
        'port-location sub-option remote-id name %s vport 1' % mac_addr,
        'dhcp-option82 enable vport 1',
        'dhcp-option82 trust true replace vport 1',
        'ip dhcp snooping enable vport 1',
        'ip-service ip-source-guard enable sport 1'
    )


# apply vlan config
@process_lock(lock_name='zte_olt')
def _zte_onu_router_config_apply(serial: str, onu_mac: str, zte_ip_addr: str, telnet_login: str,
                                 telnet_passw: str, telnet_prompt: str,
                                 user_vid: int, *args, **kwargs):
    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise expect_util.ExpectValidationError('ip address for zte not valid')

    # Входим
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
        # register onu profile on olt interface
        ch.do_cmd(
            f'onu {free_onu_number} profile line ZTE-F660-LINE remote ZTE-F660-ROUTER',
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
        template = _get_onu_template(vlan_id=user_vid, mac_addr=onu_mac)
        for line in template:
            ch.do_cmd(line, config_if_prompt)

        # Exit
        ch.do_cmd('exit', f'{telnet_prompt}(config)#')
        ch.do_cmd('exit', f'{telnet_prompt}#')
        ch.close()
        return zte_utils.zte_onu_conv_to_num(
            rack_num=rack_num,
            fiber_num=fiber_num,
            port_num=free_onu_number
        )
    else:
        ch.close()
        raise zte_utils.ZteOltConsoleError(f"I don't know what is that choice: {choice}")


class ZteF660RouterScriptModule(DeviceConfigType):
    title = 'Zte ONU F660 Router'
    short_code = 'zte_f660_router'
    accept_vlan = False

    @classmethod
    def entry_point(cls, config: dict, device, *args, **kwargs) -> OptionalScriptCallResult:
        # return
        pdev = device.parent_dev
        if not pdev:
            raise DeviceConfigurationError(_('You should config parent OLT device for ONU'))
        if not pdev.extra_data:
            raise DeviceConfigurationError(_('You have not info in extra_data '
                                             'field, please fill it in JSON'))
        zte_utils.reg_dev_zte(
            device=device,
            extra_data=dict(pdev.extra_data),
            reg_func=_zte_onu_router_config_apply,
            config=config
        )
        return {1: 'success'}
