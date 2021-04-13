from django.utils.translation import gettext_lazy as _
from devices.device_config import expect_util
from .. import zte_utils


def login_into_olt(hostname: str, login: str, password: str, prompt: str):
    ch = expect_util.MySpawn("telnet %s" % hostname)
    ch.timeout = 15
    ch.expect_exact("Username:")
    ch.do_cmd(login, "Password:")

    choice = ch.do_cmd(password, ["bad password.", "%s#" % prompt])
    if choice == 0:
        raise zte_utils.ZteOltLoginFailed
    return ch


def onu_register_template(
    register_fn, hostname: str, login: str, password: str, prompt: str, serial: str, *args, **kwargs
):
    ch = login_into_olt(hostname, login, password, prompt)

    ch.do_cmd("terminal length 0", f"{prompt}#")

    # Find unregistered onu ↓
    choice = ch.do_cmd("show gpon onu uncfg", ["No related information to show", f"{prompt}#"])
    if choice == 0:
        ch.close()
        raise zte_utils.OnuZteRegisterError(_("unregistered onu not found, sn=%s") % serial)
    if choice == 1:
        # get unregistered onu devices
        unregistered_onu = zte_utils.get_unregistered_onu(lines=ch.get_lines_before(), serial=serial)
        if unregistered_onu is None:
            ch.close()
            raise zte_utils.OnuZteRegisterError(_("unregistered onu not found, sn=%s") % serial)
        stack_num = int(unregistered_onu.get("stack_num"))
        rack_num = int(unregistered_onu.get("rack_num"))
        fiber_num = int(unregistered_onu.get("fiber_num"))

        # get last registered onu
        ch.do_cmd(f"show run int gpon-olt_{stack_num}/{rack_num}/{fiber_num}", f"{prompt}#")
        free_onu_number = zte_utils.get_free_registered_onu_number(ch.get_lines_before())
        if free_onu_number > 127:
            ch.close()
            raise zte_utils.ZTEFiberIsFull(_("olt fiber %d is full") % fiber_num)

        # enter to config
        ch.do_cmd("conf t", f"{prompt}(config)#")

        int_addr = "%d/%d/%d" % (stack_num, rack_num, fiber_num)

        # go to olt interface
        ch.do_cmd("interface gpon-olt_%s" % int_addr, "%s(config-if)#" % prompt)

        return register_fn(
            int_addr=int_addr,
            ch=ch,
            free_onu_number=free_onu_number,
            serial=serial,
            prompt=prompt,
            rack_num=rack_num,
            fiber_num=fiber_num,
            *args,
            **kwargs,
        )

    else:
        ch.close()
        raise zte_utils.ZteOltConsoleError("I don't know what is that choice: %d" % choice)
