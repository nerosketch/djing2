from typing import Iterable

from djing2.lib import RuTimedelta, safe_int
from ..epon import BDCOM_P3310C


class ZTE_C320(BDCOM_P3310C):
    description = 'OLT ZTE C320'

    def get_fibers(self):
        fibers = ({
            'fb_id': int(fiber_id),
            'fb_name': fiber_name,
            'fb_onu_num': safe_int(self.get_item('.1.3.6.1.4.1.3902.1012.3.13.1.1.13.%d' % int(fiber_id)))
        } for fiber_name, fiber_id in self.get_list_keyval('.1.3.6.1.4.1.3902.1012.3.13.1.1.1'))
        return fibers

    def get_details(self) -> dict:
        details = {
            'disk_total': self.get_item('.1.3.6.1.4.1.3902.1015.14.1.1.1.7.1.1.4.0.5.102.108.97.115.104.1'),
            'disk_free': self.get_item('.1.3.6.1.4.1.3902.1015.14.1.1.1.8.1.1.4.0.5.102.108.97.115.104.1'),
            'fname': self.get_item('.1.3.6.1.4.1.3902.1015.2.1.2.2.1.2.1.1.1'),
            'fver': self.get_item('.1.3.6.1.4.1.3902.1015.2.1.2.2.1.4.1.1.1')
        }
        details.update(super().get_details())
        return details

    # def get_ports_on_fiber(self, fiber_num: int) -> Iterable:
    #     onu_types = self.get_list_keyval('.1.3.6.1.4.1.3902.1012.3.28.1.1.1.%d' % fiber_num)
    #     onu_ports = self.get_list('.1.3.6.1.4.1.3902.1012.3.28.1.1.2.%d' % fiber_num)
    #     onu_signals = self.get_list('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.10.%d' % fiber_num)
    #
    #     # Real sn in last 3 octets
    #     onu_sns = self.get_list('.1.3.6.1.4.1.3902.1012.3.28.1.1.5.%d' % fiber_num)
    #     onu_prefixs = self.get_list('.1.3.6.1.4.1.3902.1012.3.50.11.2.1.1.%d' % fiber_num)
    #     onu_list = ({
    #         'onu_type': onu_type_num[0],
    #         'onu_port': onu_port,
    #         'onu_signal': conv_zte_signal(onu_signal),
    #         'onu_sn': onu_prefix + ''.join('%.2X' % ord(i) for i in onu_sn[-4:]),  # Real sn in last 4 octets,
    #         'snmp_extra': "%d.%d" % (fiber_num, safe_int(onu_type_num[1])),
    #     } for onu_type_num, onu_port, onu_signal, onu_sn, onu_prefix in zip(
    #         onu_types, onu_ports, onu_signals, onu_sns, onu_prefixs
    #     ))
    #
    #     return onu_list

    def get_units_unregistered(self, fiber_num: int) -> Iterable:
        sn_num_list = self.get_list_keyval('.1.3.6.1.4.1.3902.1012.3.13.3.1.2.%d' % fiber_num)
        firmware_ver = self.get_list('.1.3.6.1.4.1.3902.1012.3.13.3.1.11.%d' % fiber_num)
        loid_passws = self.get_list('.1.3.6.1.4.1.3902.1012.3.13.3.1.9.%d' % fiber_num)
        loids = self.get_list('.1.3.6.1.4.1.3902.1012.3.13.3.1.8.%d' % fiber_num)

        return ({
            'mac': ':'.join('%x' % ord(i) for i in sn[-6:]),
            'firmware_ver': frm_ver,
            'loid_passw': loid_passw,
            'loid': loid,
            'sn': 'ZTEG' + ''.join('%x' % ord(i) for i in sn[-4:]).upper()
        } for frm_ver, loid_passw, loid, (sn, num) in zip(
            firmware_ver, loid_passws, loids, sn_num_list
        ))

    def uptime(self):
        up_timestamp = safe_int(self.get_item('.1.3.6.1.2.1.1.3.0'))
        tm = RuTimedelta(seconds=up_timestamp / 100)
        return str(tm)

    def get_long_description(self):
        return self.get_item('.1.3.6.1.2.1.1.1.0')

    def get_hostname(self):
        return self.get_item('.1.3.6.1.2.1.1.5.0')
