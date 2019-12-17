from typing import Optional
from django.utils.translation import gettext_lazy as _
from djing2.lib import safe_int, RuTimedelta
from ..base import DevBase, GeneratorOrTuple, BasePort
from ..snmp_util import SNMPBaseWorker
from ..utils import plain_ip_device_mon_template

from ..dlink import DlinkDGS1100_10ME


class EltexPort(BasePort):
    def __init__(self, snmp_worker, *args, **kwargs):
        BasePort.__init__(self, *args, **kwargs)
        if not issubclass(snmp_worker.__class__, SNMPBaseWorker):
            raise TypeError
        self.snmp_worker = snmp_worker


class EltexSwitch(DlinkDGS1100_10ME):
    description = _('Eltex switch')
    is_use_device_port = False
    has_attachable_to_customer = True
    tech_code = 'eltex_sw'

    def get_ports(self) -> GeneratorOrTuple:
        def build_port(s, i: int, n: int):
            speed = self.get_item('.1.3.6.1.2.1.2.2.1.5.%d' % n)
            return EltexPort(
                s,
                num=i,
                name=self.get_item('.1.3.6.1.2.1.31.1.1.1.18.%d' % n),
                status=self.get_item('.1.3.6.1.2.1.2.2.1.8.%d' % n),
                mac=self.get_item('.1.3.6.1.2.1.2.2.1.6.%d' % n),
                uptime=self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % n),
                speed=int(speed or 0)
            )

        return tuple(build_port(self, i, n) for i, n in enumerate(range(49, 77), 1))

    def get_device_name(self):
        return self.get_item('.1.3.6.1.2.1.1.5.0')

    def uptime(self):
        uptimestamp = safe_int(self.get_item('.1.3.6.1.2.1.1.3.0'))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return tm

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.db_instance
        return plain_ip_device_mon_template(device)

    def reboot(self, save_before_reboot=False):
        return DevBase.reboot(self, save_before_reboot)

    def port_disable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num),
            2
        )

    def port_enable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num),
            1
        )
