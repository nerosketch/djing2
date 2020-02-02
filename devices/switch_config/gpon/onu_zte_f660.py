from typing import Optional, Dict
from django.utils.translation import gettext_lazy as _
from transliterate import translit

from djing2.lib import safe_int, safe_float
from ..base import DeviceConsoleError
from ..utils import norm_name
from ..expect_util import ExpectValidationError
from .f660_expect import register_onu
from .f601_expect import remove_from_olt
from ..epon import EPON_BDCOM_FORA
from .zte_utils import reg_dev_zte, sn_to_mac


def _conv_zte_signal(lvl: int) -> float:
    if lvl == 65535: return 0.0
    r = 0
    if 0 < lvl < 30000:
        r = lvl * 0.002 - 30
    elif 60000 < lvl < 65534:
        r = (lvl - 65534) * 0.002 - 30
    return round(r, 2)


class OnuZTE_F660(EPON_BDCOM_FORA):
    description = 'Zte ONU F660'
    tech_code = 'zte_onu'
    ports_len = 4

    def get_details(self) -> Optional[Dict]:
        if self.dev_instance is None:
            return
        snmp_extra = self.dev_instance.snmp_extra
        if not snmp_extra:
            return

        fiber_num, onu_num = snmp_extra.split('.')
        fiber_num, onu_num = int(fiber_num), int(onu_num)
        fiber_addr = '%d.%d' % (fiber_num, onu_num)

        signal = safe_int(self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.10.%s.1' % fiber_addr))
        distance = self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.18.%s.1' % fiber_addr)

        sn = self.get_item('.1.3.6.1.4.1.3902.1012.3.28.1.1.5.%s' % fiber_addr)
        if sn is not None:
            sn = 'ZTEG%s' % ''.join('%.2X' % x for x in sn[-4:])

        status_map = {
            '1': 'ok',
            '2': 'down'
        }
        info = {
            'status': status_map.get(self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.1.%s.1' % fiber_addr),
                                     'unknown'),
            'signal': _conv_zte_signal(signal),
            'distance': safe_float(distance) / 10,
            # 'ip_addr': self.get_item('.1.3.6.1.4.1.3902.1012.3.50.16.1.1.10.%s' % fiber_addr),
            'vlans': self.get_item('.1.3.6.1.4.1.3902.1012.3.50.15.100.1.1.7.%s.1.1' % fiber_addr),
            'serial': sn,
            'int_name': self.get_item('.1.3.6.1.4.1.3902.1012.3.28.1.1.3.%s' % fiber_addr),
            'onu_type': self.get_item('.1.3.6.1.4.1.3902.1012.3.28.1.1.1.%s' % fiber_addr),
            'mac': sn_to_mac(sn)
        }
        basic_info = super().get_details()
        if basic_info:
            info.update(basic_info)
        return info

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # for example 268501760.5
        try:
            fiber_num, onu_port = v.split('.')
            int(fiber_num), int(onu_port)
        except ValueError:
            raise ExpectValidationError(_('Zte onu snmp field must be two dot separated integers'))

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.dev_instance
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
            "\tuse				dev-onu-zte-f660",
            "\thost_name		%s" % host_name,
            "\taddress			%s" % address if address else None,
            "\t_snmp_item		%s" % snmp_item if snmp_item is not None else '',
            "\t_mac_addr		%s" % mac if mac is not None else '',
            "}\n"
        )
        return '\n'.join(i for i in r if i)

    def register_device(self, extra_data: Dict):
        return reg_dev_zte(self.dev_instance, extra_data, register_onu)

    def remove_from_olt(self, extra_data: Dict):
        dev = self.dev_instance
        if not dev:
            return False
        if not dev.parent_dev or not dev.snmp_extra:
            return False
        telnet = extra_data.get('telnet')
        if not telnet:
            return False

        fiber_num, onu_num = str(dev.snmp_extra).split('.')
        fiber_num, onu_num = safe_int(fiber_num), safe_int(onu_num)
        fiber_addr = '%d.%d' % (fiber_num, onu_num)
        sn = self.get_item('.1.3.6.1.4.1.3902.1012.3.28.1.1.5.%s' % fiber_addr)
        if sn is not None:
            sn = 'ZTEG%s' % ''.join('%.2X' % x for x in sn[-4:])
            sn_mac = sn_to_mac(sn)
            if str(dev.mac_addr) != sn_mac:
                raise ExpectValidationError(
                    _('Mac of device not equal mac by snmp')
                )
            return remove_from_olt(
                zte_ip_addr=str(dev.parent_dev.ip_address),
                telnet_login=telnet.get('login'),
                telnet_passw=telnet.get('password'),
                telnet_prompt=telnet.get('prompt'),
                snmp_info=str(dev.snmp_extra)
            )
        raise DeviceConsoleError(
            _('Could not fetch serial for onu')
        )

    def get_fiber_str(self):
        dev = self.dev_instance
        if not dev:
            return
        dat = dev.snmp_extra
        if dat and '.' in dat:
            snmp_fiber_num, onu_port_num = dat.split('.')
            snmp_fiber_num = int(snmp_fiber_num)
            bin_snmp_fiber_num = bin(snmp_fiber_num)[2:]
            rack_num = int(bin_snmp_fiber_num[5:13], 2)
            fiber_num = int(bin_snmp_fiber_num[13:21], 2)
            return 'gpon-onu_1/%d/%d:%s' % (
                rack_num, fiber_num, onu_port_num
            )
