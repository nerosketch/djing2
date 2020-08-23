import re
from typing import Optional

from djing2.lib import process_lock
from devices.device_config import expect_util
from . import zte_utils
from devices.device_config.expect_util import ExpectValidationError


def get_onu_template(vlan_id: int, mac_addr: str):
    template = (
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
    return template


def appy_config(onu_mac: str, sn: str, hostname: str, login: str, password: str, prompt: str, vlan: int):
    onu_type = 'ZTE-F660'

    # Входим
    ch = expect_util.MySpawn('telnet %s' % hostname)
    ch.timeout = 15
    ch.expect_exact('Username:')
    ch.do_cmd(login, 'Password:')

    choice = ch.do_cmd(password, ['bad password.', '%s#' % prompt])
    if choice == 0:
        raise zte_utils.ZteOltLoginFailed

    ch.do_cmd('terminal length 0', '%s#' % prompt)
    choice = ch.do_cmd('show gpon onu uncfg', ['No related information to show', '%s#' % prompt])
    if choice == 0:
        ch.close()
        raise zte_utils.OnuZteRegisterError('unregistered onu not found, sn=%s' % sn)
    elif choice == 1:
        # Получим незареганные onu
        unregistered_onu = zte_utils.get_unregistered_onu(
            lines=ch.get_lines_before(),
            serial=sn
        )
        if unregistered_onu is None:
            ch.close()
            raise zte_utils.OnuZteRegisterError('unregistered onu not found, sn=%s' % sn)
        stack_num = int(unregistered_onu.get('stack_num'))
        rack_num = int(unregistered_onu.get('rack_num'))
        fiber_num = int(unregistered_onu.get('fiber_num'))

        # Получим последнюю зарегистрированную onu
        ch.do_cmd('show run int gpon-olt_%(stack)s/%(rack)s/%(fiber)s' % {
            'stack': stack_num,
            'rack': rack_num,
            'fiber': fiber_num
        }, '%s#' % prompt)
        free_onu_number = zte_utils.get_free_registered_onu_number(
            ch.get_lines_before()
        )
        if free_onu_number > 126:
            ch.close()
            raise zte_utils.ZTEFiberIsFull('olt fiber %d is full' % fiber_num)

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
        # register onu profile on olt interface
        ch.do_cmd(
            'onu %d profile line ZTE-F660-LINE remote ZTE-F660-BRIDGE' % free_onu_number,
            '%s(config-if)#' % prompt
        )

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
        ch.do_cmd('exit', '%s#' % prompt)
        ch.close()
        return zte_utils.zte_onu_conv_to_num(
            rack_num=rack_num,
            fiber_num=fiber_num,
            port_num=free_onu_number
        )
    else:
        ch.close()
        raise zte_utils.ZteOltConsoleError("I don't know what is that choice: %d" % choice)


# Main Entry point
@process_lock(lock_name='zte_olt')
def register_onu(onu_mac: Optional[str], serial: str, zte_ip_addr: str, telnet_login: str,
                 telnet_passw: str, telnet_prompt: str, onu_vlan: int):
    serial = serial.upper()

    if not re.match(r'^ZTEG[0-9A-F]{8}$', serial):
        raise ExpectValidationError('Serial not valid, match: ^ZTEG[0-9A-F]{8}$')

    if not isinstance(onu_vlan, int):
        onu_vlan = int(onu_vlan)

    if onu_mac is None:
        onu_mac = zte_utils.sn_to_mac(serial)

    if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
        raise ExpectValidationError('ip address for zte not valid')

    return appy_config(
        onu_mac, serial, zte_ip_addr,
        telnet_login, telnet_passw,
        telnet_prompt, onu_vlan
    )
