from typing import Optional, Dict

from django.utils.translation import gettext_lazy as _
from transliterate import translit

from djing2.lib import safe_int
from devices.device_config.base import DeviceConsoleError, ListDeviceConfigType
from devices.device_config.utils import norm_name
from devices.device_config.expect_util import ExpectValidationError
from .onu_config.zte_f601_bridge_config import remove_from_olt
from .zte_utils import sn_to_mac, conv_zte_signal
from ..epon import EPON_BDCOM_FORA


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
        # distance = self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.18.%s.1' % fiber_addr)

        sn = self.get_item_plain('.1.3.6.1.4.1.3902.1012.3.28.1.1.5.%s' % fiber_addr)
        if sn is not None:
            if isinstance(sn, bytes):
                sn = 'ZTEG%s' % ''.join('%.2X' % int(x) for x in sn[-4:])
            else:
                sn = 'ZTEG%s' % ''.join('%.2X' % ord(x) for x in sn[-4:])

        status_map = {
            1: 'ok',
            2: 'down'
        }
        return {
            'status': status_map.get(
                safe_int(self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.1.%s.1' % fiber_addr)),
                'unknown'
            ),
            'signal': conv_zte_signal(signal),
            'mac': sn_to_mac(sn),
            'info': (
                (_('name'), self.get_item('.1.3.6.1.4.1.3902.1012.3.28.1.1.3.%s' % fiber_addr)),
                # 'distance': safe_float(distance) / 10,
                # 'ip_addr': self.get_item('.1.3.6.1.4.1.3902.1012.3.50.16.1.1.10.%s' % fiber_addr),
                (_('vlans'), self.get_item('.1.3.6.1.4.1.3902.1012.3.50.15.100.1.1.7.%s.1.1' % fiber_addr)),
                (_('serial'), sn),
                (_('onu_type'), self.get_item('.1.3.6.1.4.1.3902.1012.3.28.1.1.1.%s' % fiber_addr)),
            )
        }

    def default_vlan_info(self):
        default_vid = 1
        if self.dev_instance and self.dev_instance.parent_dev and self.dev_instance.parent_dev.extra_data:
            default_vid = self.dev_instance.parent_dev.extra_data.get('default_vid', 1)
        def_vids = [{'vid': default_vid, 'native': True}]
        return [
            {
                'port': 1,
                'vids': def_vids
            },
            {
                'port': 2,
                'vids': def_vids
            },
            {
                'port': 3,
                'vids': def_vids
            },
            {
                'port': 4,
                'vids': def_vids
            }
        ]

    def read_onu_vlan_info(self):
        if self.dev_instance is None:
            return
        snmp_extra = self.dev_instance.snmp_extra
        if not snmp_extra:
            return self.default_vlan_info()
        fiber_num, onu_num = snmp_extra.split('.')
        fiber_num, onu_num = int(fiber_num), int(onu_num)

        def _get_access_vlan(port_num: int) -> int:
            return safe_int(self.get_item(
                '.1.3.6.1.4.1.3902.1012.3.50.15.100.1.1.4.%(fiber_num)d.%(onu_num)d.1.%(port_num)d' % {
                    'port_num': port_num,
                    'fiber_num': fiber_num,
                    'onu_num': onu_num
                }))

        def _get_trunk_vlans(port_num: int) -> list:
            trunk_vlans = self.get_item(
                '.1.3.6.1.4.1.3902.1012.3.50.15.100.1.1.7.%(fiber_num)d.%(onu_num)d.1.%(port_num)d' % {
                    'port_num': port_num,
                    'fiber_num': fiber_num,
                    'onu_num': onu_num
                })
            trunk_vlans = list(map(int, trunk_vlans.split(b','))) if trunk_vlans else []
            return [
                {'vid': v, 'native': False}
                for v in trunk_vlans
            ]

        # Result example
        # [
        #     {
        #         'port': 1,
        #         'vids': [
        #             {'vid': 143, 'native': True},
        #             {'vid': 144, 'native': False},
        #             {'vid': 145, 'native': False},
        #         ]
        #     }
        # ]
        return (
            {
                'port': i,
                'vids': [{'vid': _get_access_vlan(port_num=i), 'native': True}] + _get_trunk_vlans(port_num=i),
            } for i in range(1, 5)
        )

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
        sn = self.get_item_plain('.1.3.6.1.4.1.3902.1012.3.28.1.1.5.%s' % fiber_addr)
        if sn is not None:
            if isinstance(sn, str):
                sn = 'ZTEG%s' % ''.join('%.2X' % ord(x) for x in sn[-4:])
            else:
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
        return super().get_fiber_str()

    @staticmethod
    def get_config_types() -> ListDeviceConfigType:
        from .onu_config.zte_f660_router_config import ZteF660RouterScriptModule
        from .onu_config.zte_f660_static_bridge_config import ZteF660BridgeStaticScriptModule
        return [ZteF660RouterScriptModule, ZteF660BridgeStaticScriptModule]
