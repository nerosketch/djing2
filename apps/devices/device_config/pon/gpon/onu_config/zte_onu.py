import re
import abc
from typing import Optional, Tuple
from pexpect import TIMEOUT

from django.utils.translation import gettext_lazy as _
from devices.device_config import expect_util
from devices.device_config.base import OptionalScriptCallResult, DeviceConfigType, DeviceConfigurationError
from djing2.lib import process_lock, safe_int
from .. import zte_utils
from ...utils import get_all_vlans_from_config


class ZteOnuDeviceConfigType(DeviceConfigType):
    title = ""
    short_code = ""
    accept_vlan = False
    zte_type = None
    ch = None

    def __del__(self):
        if self.ch is not None and not self.ch.closed:
            self.ch.close()
            self.ch = None

    def entry_point(self, config: dict, device, *args, **kwargs) -> OptionalScriptCallResult:
        extra_data = self.get_extra_data(device)

        ip = None
        if device.ip_address:
            ip = device.ip_address
        elif device.parent_dev:
            ip = device.parent_dev.ip_address
            if not ip:
                raise DeviceConfigurationError("not have ip")
        mac = str(device.mac_addr) if device.mac_addr else None

        # Format serial number from mac address
        # because saved mac address got from serial number
        sn = "ZTEG%s" % "".join("%.2X" % int(x, base=16) for x in mac.split(":")[-4:])
        telnet = extra_data.get("telnet")

        @process_lock(lock_name="zte_olt")
        def _locked_register_onu(device_config_type: ZteOnuDeviceConfigType, *args, **kwargs):
            return device_config_type.register_onu(*args, **kwargs)

        try:
            onu_snmp = _locked_register_onu(
                self,
                onu_mac=mac,
                serial=sn.upper(),
                zte_ip_addr=str(ip),
                telnet_login=telnet.get("login"),
                telnet_password=telnet.get("password"),
                telnet_prompt=telnet.get("prompt"),
                config=config,
                snmp_info=str(device.snmp_extra),
                user_vid=extra_data.get("default_vid"),
            )
            if onu_snmp is not None:
                device.snmp_extra = onu_snmp
                device.save(update_fields=("snmp_extra",))
            else:
                raise DeviceConfigurationError(_("unregistered onu not found, sn=%s") % sn)
        except TIMEOUT as e:
            raise zte_utils.OnuZteRegisterError(e)

        return {1: "success"}

    @staticmethod
    def get_extra_data(device) -> dict:
        pdev = device.parent_dev
        if not pdev:
            raise DeviceConfigurationError(_("You should config parent OLT device for ONU"))
        if not pdev.extra_data:
            raise DeviceConfigurationError(_("You have not info in extra_data " "field, please fill it in JSON"))

        extra_data = dict(pdev.extra_data)
        if not extra_data:
            raise DeviceConfigurationError(_("You have not info in extra_data " "field, please fill it in JSON"))
        return extra_data

    @staticmethod
    def login_into_olt(hostname: str, login: str, password: str, prompt: str) -> expect_util.MySpawn:
        ch = expect_util.MySpawn("telnet %s" % hostname)
        ch.timeout = 25
        ch.expect_exact("Username:")
        ch.do_cmd(login, "Password:")

        choice = ch.do_cmd(password, ["bad password.", "%s#" % prompt])
        if choice == 0:
            raise zte_utils.ZteOltLoginFailed

        ch.do_cmd("terminal length 0", f"{prompt}#")
        return ch

    def register_onu(
        self,
        serial: str,
        config: dict,
        onu_mac: str,
        zte_ip_addr: str,
        telnet_login: str,
        telnet_password: str,
        telnet_prompt: str,
        *args,
        **kwargs,
    ) -> Optional[str]:
        if not re.match(r"^ZTEG[0-9A-F]{8}$", serial):
            raise expect_util.ExpectValidationError("Serial not valid, match: ^ZTEG[0-9A-F]{8}$")

        all_vids = get_all_vlans_from_config(config=config)
        if not all_vids:
            raise zte_utils.OnuZteRegisterError("not passed vlan list")

        onu_vlan = safe_int(all_vids[0])
        if onu_vlan == 0:
            raise zte_utils.OnuZteRegisterError("Bad vlan passed in config")

        if not re.match(expect_util.IP4_ADDR_REGEX, zte_ip_addr):
            raise expect_util.ExpectValidationError("ip address for zte not valid")

        ch = self.login_into_olt(zte_ip_addr, telnet_login, telnet_password, telnet_prompt)
        self.ch = ch

        stack_num, rack_num, fiber_num = self.find_unregistered_onu(prompt=telnet_prompt, serial=serial)

        free_onu_number = self.get_last_registered_onu_number(
            stack_num=stack_num, rack_num=rack_num, fiber_num=fiber_num, prompt=telnet_prompt
        )

        # enter to config
        ch.do_cmd("conf t", f"{telnet_prompt}(config)#")

        int_addr = "%d/%d/%d" % (stack_num, rack_num, fiber_num)

        self.register_onu_on_olt_interface(
            free_onu_number=free_onu_number,
            serial=serial,
            prompt=telnet_prompt,
            onu_type=self.zte_type,
            int_addr=int_addr,
        )

        self.apply_zte_top_conf(
            prompt=telnet_prompt,
            free_onu_number=free_onu_number,
            int_addr=int_addr,
            user_vid=onu_vlan,
            onu_mac=onu_mac,
            all_vids=all_vids,
            config=config,
        )

        self.apply_zte_bot_conf(
            prompt=telnet_prompt,
            int_addr=int_addr,
            free_onu_number=free_onu_number,
            user_vid=onu_vlan,
            all_vids=all_vids,
            config=config,
        )

        ch.do_cmd("exit", "%s#" % telnet_prompt)
        ch.sendline("exit")

        ch.close()
        return zte_utils.zte_onu_conv_to_num(rack_num=rack_num, fiber_num=fiber_num, port_num=free_onu_number)

    def find_unregistered_onu(self, prompt: str, serial: str) -> Tuple[int, int, int]:
        # Find unregistered onu ↓
        ch = self.ch
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
            return stack_num, rack_num, fiber_num
        else:
            ch.close()
            raise zte_utils.ZteOltConsoleError("I don't know what is that choice: %d" % choice)

    def get_last_registered_onu_number(self, stack_num: int, rack_num: int, fiber_num: int, prompt: str) -> int:
        # get last registered onu
        self.ch.do_cmd(f"show run int gpon-olt_{stack_num}/{rack_num}/{fiber_num}", f"{prompt}#")
        free_onu_number = zte_utils.get_free_registered_onu_number(self.ch.get_lines_before())
        if free_onu_number > 127:
            self.ch.close()
            raise zte_utils.ZTEFiberIsFull(_("olt fiber %d is full") % fiber_num)
        return free_onu_number

    def register_onu_on_olt_interface(
        self, free_onu_number: int, serial: str, prompt: str, onu_type: str, int_addr: str
    ) -> None:

        # go to olt interface
        self.ch.do_cmd("interface gpon-olt_%s" % int_addr, "%s(config-if)#" % prompt)

        # register onu on olt interface
        self.ch.do_cmd("onu %d type %s sn %s" % (free_onu_number, onu_type, serial), "%s(config-if)#" % prompt)

        # Exit from int olt
        self.ch.do_cmd("exit", "%s(config)#" % prompt)

    @abc.abstractmethod
    def apply_zte_top_conf(self, *args, **kwargs) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def apply_zte_bot_conf(self, *args, **kwargs):
        raise NotImplementedError
