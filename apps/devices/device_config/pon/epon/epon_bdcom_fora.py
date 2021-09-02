from typing import Dict
from django.utils.translation import gettext, gettext_lazy as _
from easysnmp import EasySNMPTimeoutError

from djing2.lib import safe_int, safe_float, macbin2str, RuTimedelta, bytes2human
from devices.device_config.base import DeviceImplementationError, DeviceConfigurationError
from devices.device_config.expect_util import ExpectValidationError
from .epon_bdcom_expect import remove_from_olt
from ..pon_device_strategy import PonOnuDeviceStrategy


class EPON_BDCOM_FORA(PonOnuDeviceStrategy):
    has_attachable_to_customer = True
    description = "PON ONU BDCOM"
    tech_code = "bdcom_onu"
    is_use_device_port = False
    ports_len = 1

    def __init__(self, *args, **kwargs):
        super(EPON_BDCOM_FORA, self).__init__(*args, **kwargs)
        dev_ip_addr = None
        dev_instance = self.model_instance
        if dev_instance.ip_address:
            dev_ip_addr = dev_instance.ip_address
        else:
            parent_device = dev_instance.parent_dev
            if parent_device is not None and parent_device.ip_address:
                dev_ip_addr = parent_device.ip_address
        if dev_ip_addr is None:
            raise DeviceImplementationError(
                gettext("Ip address or parent device with ip address required for ONU device")
            )
        if not dev_instance.man_passw:
            raise DeviceImplementationError(gettext("For fetch additional device info, snmp community required"))
        super().__init__(
            dev_instance=dev_instance, host=dev_ip_addr, snmp_community=str(dev_instance.man_passw), *args, **kwargs
        )

    def get_device_name(self):
        pass

    def get_uptime(self):
        pass

    def get_details(self):
        if self.model_instance is None:
            return
        num = safe_int(self.model_instance.snmp_extra)
        if not num:
            return
        status_map = {3: "ok", 2: "down"}
        try:
            # https://www.zabbix.com/documentation/1.8/ru/manual/advanced_snmp
            status = safe_int(self.get_item(".1.3.6.1.4.1.3320.101.10.1.1.26.%d" % num))
            signal = safe_float(self.get_item(".1.3.6.1.4.1.3320.101.10.5.1.5.%d" % num))
            # distance = self.get_item('.1.3.6.1.4.1.3320.101.10.1.1.27.%d' % num)
            mac = self.get_item_plain(".1.3.6.1.4.1.3320.101.10.1.1.3.%d" % num)
            uptime = safe_int(self.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % num))
            if uptime > 0:
                uptime = RuTimedelta(seconds=uptime / 100)
            # speed = self.get_item('.1.3.6.1.2.1.2.2.1.5.%d' % num)
            if status > 0:
                return {
                    "status": status_map.get(status, "unknown"),
                    "signal": signal / 10 if signal else "—",
                    "mac": macbin2str(mac),
                    "info": (
                        # IF-MIB::ifDescr
                        (_("name"), self.get_item(".1.3.6.1.2.1.2.2.1.2.%d" % num)),
                        # IF-MIB::ifMtu
                        (_("mtu"), self.get_item(".1.3.6.1.2.1.2.2.1.4.%d" % num)),
                        # IF-MIB::ifInOctets
                        (_("in_octets"), bytes2human(safe_float(self.get_item(".1.3.6.1.2.1.2.2.1.10.%d" % num)))),
                        # IF-MIB::ifInUcastPkts
                        (_("in_ucst_pkts"), self.get_item(".1.3.6.1.2.1.2.2.1.11.%d" % num)),
                        # IF-MIB::ifInNUcastPkts
                        (_("in_not_ucst_pkts"), self.get_item(".1.3.6.1.2.1.2.2.1.12.%d" % num)),
                        # IF-MIB::ifInDiscards
                        (_("in_discards"), self.get_item(".1.3.6.1.2.1.2.2.1.13.%d" % num)),
                        # IF-MIB::ifInErrors
                        (_("in_errors"), self.get_item(".1.3.6.1.2.1.2.2.1.14.%d" % num)),
                        # IF-MIB::ifOutOctets
                        (_("out_octets"), bytes2human(safe_float(self.get_item(".1.3.6.1.2.1.2.2.1.16.%d" % num)))),
                        # IF-MIB::ifOutUcastPkts
                        (_("out_ucst_pkts"), self.get_item(".1.3.6.1.2.1.2.2.1.17.%d" % num)),
                        # IF-MIB::ifOutNUcastPkts
                        (_("out_not_ucst_pkts"), self.get_item(".1.3.6.1.2.1.2.2.1.18.%d" % num)),
                        # IF-MIB::ifOutDiscards
                        (_("out_discards"), self.get_item(".1.3.6.1.2.1.2.2.1.19.%d" % num)),
                        # IF-MIB::ifOutErrors
                        (_("out_errors"), self.get_item(".1.3.6.1.2.1.2.2.1.20.%d" % num)),
                        (_("uptime"), str(uptime)),
                    ),
                }
        except EasySNMPTimeoutError as e:
            return {"err": "{}: {}".format(_("ONU not connected"), e)}

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # DBCOM Onu have en integer snmp port
        try:
            int(v)
        except ValueError:
            raise ExpectValidationError(_("Onu snmp field must be en integer"))

    def remove_from_olt(self, extra_data: Dict, **kwargs):
        dev = self.model_instance
        if not dev:
            return False
        if not dev.parent_dev or not dev.snmp_extra:
            return False
        telnet = extra_data.get("telnet")
        if not telnet:
            return False
        onu_sn, err_text = dev.onu_find_sn_by_mac()
        if onu_sn is None:
            raise DeviceConfigurationError(err_text)
        return remove_from_olt(
            ip_addr=str(dev.parent_dev.ip_address),
            telnet_login=telnet.get("login"),
            telnet_passw=telnet.get("password"),
            telnet_prompt=telnet.get("prompt"),
            int_name=self.get_item(".1.3.6.1.2.1.2.2.1.2.%d" % onu_sn),
        )


SwitchDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, DlinkDGS_3120_24SCSwitchInterface)
