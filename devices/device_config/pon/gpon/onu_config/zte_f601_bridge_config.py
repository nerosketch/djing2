import re
from typing import Optional

from django.utils.translation import gettext_lazy as _

from devices.device_config import expect_util
from devices.device_config.base import OptionalScriptCallResult, DeviceConfigType, DeviceConfigurationError
from devices.device_config.pon.utils import get_all_vlans_from_config
from djing2.lib import process_lock, safe_int
from ..zte_utils import (
    get_unregistered_onu, get_free_registered_onu_number,
    zte_onu_conv_to_num, sn_to_mac, zte_onu_conv_from_onu,
    ZteOltLoginFailed, OnuZteRegisterError, ZTEFiberIsFull,
    ZteOltConsoleError, reg_dev_zte
)


def get_onu_template(vlan_id: int, mac_addr: str):
    template = (
        'sn-bind enable sn',
        'tcont 1 profile HSI_100',
        'gemport 1 unicast tcont 1 dir both',
        'security storm-control broadcast rate 8 direction ingress vport 1',
        'security storm-control broadcast rate 8 direction egress vport 1',
        'switchport mode hybrid vport 1',
        'service-port 1 vport 1 user-vlan %d vlan %d' % (vlan_id, vlan_id),
        'port-location format flexible-syntax vport 1',
        'port-location sub-option remote-id enable vport 1',
        'port-location sub-option remote-id name %s vport 1' % mac_addr,
        'dhcp-option82 enable vport 1',
        'dhcp-option82 trust true replace vport 1',
        'ip dhcp snooping enable vport 1',
        # 'ip-service ip-source-guard enable sport 1'
    )
    return template


def get_pon_mng_template(vlan_id: int):
    template = (
        'service HSI type internet gemport 1 vlan %d' % vlan_id,
        'loop-detect ethuni eth_0/1 enable',
        'vlan port eth_0/1 mode tag vlan %d' % vlan_id,
        'dhcp-ip ethuni eth_0/1 from-internet'
    )
    return template


def appy_config(onu_mac: str, sn: str, hostname: str, login: str, password: str, prompt: str, vlan: int):
    onu_type = 'ZTE-F601'
    sn = sn.upper()

    # Входим
    ch = expect_util.MySpawn('telnet %s' % hostname)
    ch.timeout = 15
    ch.expect_exact('Username:')
    ch.do_cmd(login, 'Password:')

    choice = ch.do_cmd(password, ['bad password.', '%s#' % prompt])
    if choice == 0:
        raise ZteOltLoginFailed

    ch.do_cmd('terminal length 0', '%s#' % prompt)
    choice = ch.do_cmd('show gpon onu uncfg', ['No related information to show', '%s#' % prompt])

    if choice == 0:
        ch.close()
        raise OnuZteRegisterError(_('unregistered onu not found, sn=%s') % sn)
    elif choice == 1:
        # Получим незареганные onu
        unregistered_onu = get_unregistered_onu(
            lines=ch.get_lines_before(),
            serial=sn
        )
        if unregistered_onu is None:
            ch.close()
            raise OnuZteRegisterError(_('unregistered onu not found, sn=%s') % sn)

        stack_num = int(unregistered_onu.get('stack_num'))
        rack_num = int(unregistered_onu.get('rack_num'))
        fiber_num = int(unregistered_onu.get('fiber_num'))

        # Получим последнюю зарегистрированную onu
        ch.do_cmd('show run int gpon-olt_%(stack)s/%(rack)s/%(fiber)s' % {
            'stack': stack_num,
            'rack': rack_num,
            'fiber': fiber_num
        }, '%s#' % prompt)
        free_onu_number = get_free_registered_onu_number(
            ch.get_lines_before()
        )

        if free_onu_number > 126:
            ch.close()
            raise ZTEFiberIsFull(_('olt fiber %d is full') % fiber_num)

        # enter to config
        ch.do_cmd('conf t', '%s(config)#' % prompt)

        int_addr = '%d/%d/%d' % (
            stack_num,
            rack_num,
            fiber_num
        )

        # go to olt interface
        ch.do_cmd('interface gpon-olt_%s' % int_addr, '%s(config-if)#' % prompt)

        # register onu on olt interface
        ch.do_cmd('onu %d type %s sn %s' % (
            free_onu_number,
            onu_type,
            sn
        ), '%s(config-if)#' % prompt)

        # Exit from int olt
        ch.do_cmd('exit', '%s(config)#' % prompt)

        # Enter to int onu
        ch.do_cmd('int gpon-onu_%(int_addr)s:%(onu_num)d' % {
            'int_addr': int_addr,
            'onu_num': free_onu_number
        }, '%s(config-if)#' % prompt)

        # Apply int onu config
        template = get_onu_template(vlan, onu_mac)
        for line in template:
            ch.do_cmd(line, '%s(config-if)#' % prompt)

        # Exit
        ch.do_cmd('exit', '%s(config)#' % prompt)

        # Enter to pon-onu-mng
        ch.do_cmd('pon-onu-mng gpon-onu_%(int_addr)s:%(onu_num)d' % {
            'int_addr': int_addr,
            'onu_num': free_onu_number
        }, '%s(gpon-onu-mng)#' % prompt)

        # Apply config to pon-onu-mng
        for line in get_pon_mng_template(vlan):
            ch.do_cmd(line, '%s(gpon-onu-mng)#' % prompt)

        # Exit
        ch.do_cmd('exit', '%s(config)#' % prompt)
        ch.do_cmd('exit', '%s#' % prompt)
        ch.sendline('exit')

        ch.close()
        return zte_onu_conv_to_num(
            rack_num=rack_num,
            fiber_num=fiber_num,
            port_num=free_onu_number
        )
    else:
        ch.close()
        raise ZteOltConsoleError("I don't know what is that choice: %d" % choice)


# Main Entry point
@process_lock(lock_name='zte_olt')
def _register_onu(onu_mac: Optional[str], serial: str, zte_ip_addr: str, telnet_login: str,
                  telnet_passw: str, telnet_prompt: str, config: dict,
                  *args, **kwargs):
    serial = serial.upper()

    if not re.match(r'^ZTEG[0-9A-F]{8}$', serial):
        raise expect_util.ExpectValidationError('Serial not valid, match: ^ZTEG[0-9A-F]{8}$')

    all_vids = get_all_vlans_from_config(config=config)
    if not all_vids:
        raise OnuZteRegisterError(f'not passed vlan list')

    onu_vlan = safe_int(all_vids[0])
    if onu_vlan == 0:
        raise OnuZteRegisterError('Bad vlan passed in config')

    if onu_mac is None:
        onu_mac = sn_to_mac(serial)

    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise expect_util.ExpectValidationError('ip address for zte not valid')

    return appy_config(
        onu_mac, serial, zte_ip_addr,
        telnet_login, telnet_passw,
        telnet_prompt, onu_vlan
    )


@process_lock(lock_name='zte_olt')
def remove_from_olt(zte_ip_addr: str, telnet_login: str,
                    telnet_passw: str, telnet_prompt: str, snmp_info: str,
                    *args, **kwargs):
    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise expect_util.ExpectValidationError('ip address for zte not valid')

    # Входим
    ch = expect_util.MySpawn('telnet %s' % zte_ip_addr)
    ch.timeout = 15
    ch.expect_exact('Username:')
    ch.do_cmd(telnet_login, 'Password:')

    choice = ch.do_cmd(telnet_passw, ['bad password.', '%s#' % telnet_prompt])
    if choice == 0:
        raise ZteOltLoginFailed

    rack_num, fiber_num, onu_num = zte_onu_conv_from_onu(snmp_info)

    # enter to config
    ch.do_cmd('conf t', '%s(config)#' % telnet_prompt)

    int_addr = '1/%d/%d' % (
        rack_num,
        fiber_num
    )
    # go to olt interface
    ch.do_cmd('interface gpon-olt_%s' % int_addr, '%s(config-if)#' % telnet_prompt)

    # remove onu register from olt fiber
    ch.do_cmd('no onu %d' % onu_num, '%s(config-if)#' % telnet_prompt)

    # Exit
    ch.do_cmd('exit', '%s(config)#' % telnet_prompt)
    ch.do_cmd('exit', '%s#' % telnet_prompt)
    ch.sendline('exit')
    ch.close()
    return True


class ZteF601BridgeScriptModule(DeviceConfigType):
    title = 'Zte F601 dhcp'
    short_code = 'zte_f601_bridge'
    accept_vlan = True

    @classmethod
    def entry_point(cls, config: dict, device, *args, **kwargs) -> OptionalScriptCallResult:
        pdev = device.parent_dev
        if not pdev:
            raise DeviceConfigurationError(_('You should config parent OLT device for ONU'))
        if not pdev.extra_data:
            raise DeviceConfigurationError(_('You have not info in extra_data '
                                             'field, please fill it in JSON'))
        reg_dev_zte(
            device=device,
            extra_data=dict(pdev.extra_data),
            reg_func=_register_onu,
            config=config
        )
        return {1: 'success'}
