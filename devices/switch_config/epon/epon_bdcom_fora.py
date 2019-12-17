from typing import Optional, Dict
from django.utils.translation import gettext, gettext_lazy as _
from easysnmp import EasySNMPTimeoutError
from transliterate import translit

from djing2.lib import safe_int, safe_float
from ..base import GeneratorOrTuple, DevBase, DeviceImplementationError, DeviceConfigurationError
from ..snmp_util import SNMPBaseWorker
from ..utils import norm_name
from ..expect_util import ExpectValidationError
from .epon_bdcom_expect import remove_from_olt


class EPON_BDCOM_FORA(DevBase, SNMPBaseWorker):
    has_attachable_to_customer = True
    description = 'PON ONU BDCOM'
    tech_code = 'bdcom_onu'
    is_use_device_port = False

    def __init__(self, dev_instance):
        DevBase.__init__(self, dev_instance)
        dev_ip_addr = None
        if dev_instance.ip_address:
            dev_ip_addr = dev_instance.ip_address
        else:
            parent_device = dev_instance.parent_dev
            if parent_device is not None and parent_device.ip_address:
                dev_ip_addr = parent_device.ip_address
        if dev_ip_addr is None:
            raise DeviceImplementationError(gettext(
                'Ip address or parent device with ip address required for ONU device'
            ))
        if not dev_instance.man_passw:
            raise DeviceImplementationError(gettext(
                'For fetch additional device info, snmp community required'
            ))
        SNMPBaseWorker.__init__(self, dev_ip_addr, dev_instance.man_passw, 2)

    def get_ports(self) -> GeneratorOrTuple:
        return ()

    def get_device_name(self):
        pass

    def uptime(self):
        pass

    def get_details(self):
        if self.db_instance is None:
            return
        num = safe_int(self.db_instance.snmp_extra)
        if not num:
            return
        status_map = {
            '3': 'ok',
            '2': 'down'
        }
        try:
            status = self.get_item('.1.3.6.1.4.1.3320.101.10.1.1.26.%d' % num)
            signal = safe_float(self.get_item('.1.3.6.1.4.1.3320.101.10.5.1.5.%d' % num))
            distance = self.get_item('.1.3.6.1.4.1.3320.101.10.1.1.27.%d' % num)
            mac = self.get_item('.1.3.6.1.4.1.3320.101.10.1.1.3.%d' % num)
            if mac is not None:
                mac = ':'.join('%x' % ord(i) for i in mac)
            # uptime = self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % num)
            if status is not None and status.isdigit():
                basic_info = super().get_details()
                basic_info.update({
                    'status': status_map.get(status, 'unknown'),
                    'signal': signal / 10 if signal else '—',
                    'name': self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % num),
                    'mac': mac,
                    'distance': int(distance) / 10 if distance.isdigit() else 0
                })
                return basic_info
        except EasySNMPTimeoutError as e:
            return {'err': "%s: %s" % (_('ONU not connected'), e)}

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # DBCOM Onu have en integer snmp port
        try:
            int(v)
        except ValueError:
            raise ExpectValidationError(_('Onu snmp field must be en integer'))

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.db_instance
        if not device:
            return
        host_name = norm_name("%d%s" % (device.pk, translit(device.comment, language_code='ru', reversed=True)))
        snmp_item = device.snmp_extra
        mac = device.mac_addr
        if device.ip_address:
            address = device.ip_address
        elif device.parent_dev:
            address = device.parent_dev.ip_address
        else:
            address = None
        r = (
            "define host{",
            "\tuse				device-onu",
            "\thost_name		%s" % host_name,
            "\taddress			%s" % address if address else None,
            "\t_snmp_item		%s" % snmp_item if snmp_item is not None else '',
            "\t_mac_addr		%s" % mac if mac is not None else '',
            "}\n"
        )
        return '\n'.join(i for i in r if i)

    def register_device(self, extra_data: Dict):
        pass

    def remove_from_olt(self, extra_data: Dict):
        dev = self.db_instance
        if not dev:
            return False
        if not dev.parent_dev or not dev.snmp_extra:
            return False
        telnet = extra_data.get('telnet')
        if not telnet:
            return False
        onu_sn, err_text = dev.onu_find_sn_by_mac()
        if onu_sn is None:
            raise DeviceConfigurationError(err_text)
        return remove_from_olt(
            ip_addr=str(dev.parent_dev.ip_address),
            telnet_login=telnet.get('login'),
            telnet_passw=telnet.get('password'),
            telnet_prompt=telnet.get('prompt'),
            int_name=self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % onu_sn)
        )

    def port_disable(self, port_num: int):
        pass

    def port_enable(self, port_num: int):
        pass
