import re
from django.utils.translation import gettext
from djing2.lib import process_lock, safe_int
from devices.device_config.base import DeviceConsoleError, DeviceImplementationError
from devices.device_config import expect_util


@process_lock()
def remove_from_olt(ip_addr: str, telnet_login: str, telnet_passw: str,
                    telnet_prompt: str, int_name: str):
    if not re.match(expect_util.IP4_ADDR_REGEX, ip_addr):
        raise expect_util.ExpectValidationError('ip address for OLT not valid')

    # Split "EPON0/1:17" for fiber_num - 1, and onu_num - 17
    try:
        fiber_num, onu_num = int_name.split('/')[1].split(':')
        fiber_num, onu_num = safe_int(fiber_num), safe_int(onu_num)
    except (IndexError, ValueError):
        raise DeviceImplementationError('Device interface unexpected')

    if onu_num < 1 or onu_num > 64:
        raise DeviceImplementationError('Onu num must be in range 1-64')

    # Enter
    ch = expect_util.MySpawn('telnet %s' % ip_addr)
    ch.timeout = 15
    ch.expect_exact('Username: ')
    ch.do_cmd(telnet_login, 'Password: ')

    choice = ch.do_cmd(telnet_passw, ['Authentication failed!', '%s>' % telnet_prompt])
    if choice == 0:
        raise DeviceConsoleError(
            gettext('Wrong login or password for telnet access')
        )

    # enable privileges
    ch.do_cmd('enable', '%s#' % telnet_prompt)

    # enter to config
    ch.do_cmd('config', '%s_config#' % telnet_prompt)

    fiber_prompt = '%s_config_epon0/%d#' % (telnet_prompt, fiber_num)

    # enter to fiber
    ch.do_cmd('int EPON0/%d' % fiber_num, fiber_prompt)

    # unbind onu
    ch.do_cmd("no epon bind-onu sequence %d" % onu_num, fiber_prompt)

    # end removing
    ch.close()
    return True
