from django.utils.translation import gettext, gettext_lazy as _
from easysnmp import EasySNMPTimeoutError

from djing2.lib import safe_int, safe_float, macbin2str, RuTimedelta, bytes2human
from devices.device_config.base import (
    DeviceImplementationError, DeviceConfigurationError,
    Vlans, Vlan
)
from devices.device_config.expect_util import ExpectValidationError
from .epon_bdcom_expect import remove_from_olt
from ..pon_device_strategy import PonOnuDeviceStrategy, PonONUDeviceStrategyContext
from ...base_device_strategy import SNMPWorker

_DEVICE_UNIQUE_CODE = 3


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

    def get_device_name(self):
        return 'fora'

    def get_uptime(self):
        return '0'

    def get_details(self):
        dev = self.model_instance
        if dev is None:
            return {}
        num = safe_int(dev.snmp_extra)
        if not num:
            return {}
        parent = dev.parent_dev
        if not parent:
            return {}
        status_map = {3: "ok", 2: "down"}
        snmp = SNMPWorker(hostname=parent.ip_address, community=str(parent.man_passw))
        try:
            # https://www.zabbix.com/documentation/1.8/ru/manual/advanced_snmp
            status = safe_int(snmp.get_item(".1.3.6.1.4.1.3320.101.10.1.1.26.%d" % num))
            signal = safe_float(snmp.get_item(".1.3.6.1.4.1.3320.101.10.5.1.5.%d" % num))
            # distance = snmp.get_item('.1.3.6.1.4.1.3320.101.10.1.1.27.%d' % num)
            mac = snmp.get_item_plain(".1.3.6.1.4.1.3320.101.10.1.1.3.%d" % num)
            uptime = safe_int(snmp.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % num))
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
                        (_("name"), snmp.get_item(".1.3.6.1.2.1.2.2.1.2.%d" % num)),
                        # IF-MIB::ifMtu
                        (_("mtu"), snmp.get_item(".1.3.6.1.2.1.2.2.1.4.%d" % num)),
                        # IF-MIB::ifInOctets
                        (_("in_octets"), bytes2human(safe_float(snmp.get_item(".1.3.6.1.2.1.2.2.1.10.%d" % num)))),
                        # IF-MIB::ifInUcastPkts
                        (_("in_ucst_pkts"), snmp.get_item(".1.3.6.1.2.1.2.2.1.11.%d" % num)),
                        # IF-MIB::ifInNUcastPkts
                        (_("in_not_ucst_pkts"), snmp.get_item(".1.3.6.1.2.1.2.2.1.12.%d" % num)),
                        # IF-MIB::ifInDiscards
                        (_("in_discards"), snmp.get_item(".1.3.6.1.2.1.2.2.1.13.%d" % num)),
                        # IF-MIB::ifInErrors
                        (_("in_errors"), snmp.get_item(".1.3.6.1.2.1.2.2.1.14.%d" % num)),
                        # IF-MIB::ifOutOctets
                        (_("out_octets"), bytes2human(safe_float(snmp.get_item(".1.3.6.1.2.1.2.2.1.16.%d" % num)))),
                        # IF-MIB::ifOutUcastPkts
                        (_("out_ucst_pkts"), snmp.get_item(".1.3.6.1.2.1.2.2.1.17.%d" % num)),
                        # IF-MIB::ifOutNUcastPkts
                        (_("out_not_ucst_pkts"), snmp.get_item(".1.3.6.1.2.1.2.2.1.18.%d" % num)),
                        # IF-MIB::ifOutDiscards
                        (_("out_discards"), snmp.get_item(".1.3.6.1.2.1.2.2.1.19.%d" % num)),
                        # IF-MIB::ifOutErrors
                        (_("out_errors"), snmp.get_item(".1.3.6.1.2.1.2.2.1.20.%d" % num)),
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
        except ValueError as err:
            raise ExpectValidationError(_("Onu snmp field must be en integer")) from err

    def remove_from_olt(self, extra_data: dict, **kwargs):
        dev = self.model_instance
        if not dev:
            return False
        if not dev.parent_dev or not dev.snmp_extra:
            return False
        telnet = extra_data.get("telnet")
        if not telnet:
            return False
        onu_sn, err_text = self.find_onu()
        if onu_sn is None:
            raise DeviceConfigurationError(err_text)
        parent = dev.parent_dev
        with SNMPWorker(hostname=parent.ip_address, community=str(parent.man_passw)) as snmp:
            int_name = snmp.get_item(".1.3.6.1.2.1.2.2.1.2.%d" % onu_sn)
        return remove_from_olt(
            ip_addr=str(parent.ip_address),
            telnet_login=telnet.get("login"),
            telnet_passw=telnet.get("password"),
            telnet_prompt=telnet.get("prompt"),
            int_name=int_name,
        )

    def read_onu_vlan_info(self):
        return []

    def default_vlan_info(self):
        return []

    def read_all_vlan_info(self) -> Vlans:
        yield Vlan(vid=1, title='Default')

    def find_onu(self, *args, **kwargs):
        dev = self.model_instance
        parent = dev.parent_dev
        if parent is not None:
            mac = dev.mac_addr
            snmp = SNMPWorker(hostname=parent.ip_address, community=str(parent.man_passw))
            onu_macs = snmp.get_list_keyval(".1.3.6.1.4.1.3320.101.10.1.1.3")
            for srcmac, snmpnum in onu_macs:
                # convert bytes mac address to str presentation mac address
                real_mac = macbin2str(srcmac)
                if mac == real_mac:
                    return safe_int(snmpnum), None
            return None, _('Onu with mac "%(onu_mac)s" not found on OLT') % {"onu_mac": mac}
        return None, _("Parent device not found")


PonONUDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, EPON_BDCOM_FORA)
