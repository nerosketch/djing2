from typing import Optional, Dict
from easysnmp import EasySNMPTimeoutError
from django.utils.translation import gettext
from djing2.lib import safe_int, RuTimedelta, safe_float
from ..utils import plain_ip_device_mon_template
from ..base import DevBase, BasePort, GeneratorOrTuple
from ..snmp_util import SNMPBaseWorker


class ONUdevPort(BasePort):
    def __init__(self, signal, snmp_worker, *args, **kwargs):
        super(ONUdevPort, self).__init__(*args, **kwargs)
        if not issubclass(snmp_worker.__class__, SNMPBaseWorker):
            raise TypeError
        self.snmp_worker = snmp_worker
        self.signal = signal

    def to_dict(self):
        sdata = super().to_dict()
        sdata.update({
            'signal': self.signal
        })
        return sdata

    def __str__(self):
        return "%d: '%s' %s" % (self.num, self.nm, self.mac())


class BDCOM_P3310C(DevBase, SNMPBaseWorker):
    has_attachable_to_customer = False
    description = 'PON OLT'
    is_use_device_port = False

    def __init__(self, dev_instance):
        DevBase.__init__(self, dev_instance)
        SNMPBaseWorker.__init__(self, dev_instance.ip_address, dev_instance.man_passw, 2)

    def get_ports(self) -> GeneratorOrTuple:
        """
        If fast operation then just return tuple.
        If long operation then return the generator of ports count first,
        then max chunk size, and ports in next in generations
        """
        # numbers
        # fiber_nums = (safe_int(i) for i in self.get_list('.1.3.6.1.4.1.3320.101.6.1.1.1'))
        # numbers
        fiber_onu_counts = self.get_list('.1.3.6.1.4.1.3320.101.6.1.1.2')

        # comma separated strings, remember to remove empty elements
        fiber_onu_nums = self.get_list('.1.3.6.1.4.1.3320.101.6.1.1.23')

        # All onu's count
        yield sum(safe_int(i) for i in fiber_onu_counts)

        # chunk max size
        yield 200

        try:
            for fiber_onu_num in fiber_onu_nums:
                for onu_num in fiber_onu_num.split(','):
                    if not onu_num:
                        continue
                    onu_num = safe_int(onu_num)
                    if onu_num == 0:
                        continue
                    status = self.get_item('.1.3.6.1.4.1.3320.101.10.1.1.26.%d' % onu_num)
                    signal = safe_float(self.get_item('.1.3.6.1.4.1.3320.101.10.5.1.5.%d' % onu_num))
                    yield ONUdevPort(
                        num=onu_num,
                        name=self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % onu_num),
                        status=status == '3',
                        mac=self.get_item('.1.3.6.1.4.1.3320.101.10.1.1.3.%d' % onu_num),
                        speed=0,
                        signal=signal / 10 if signal else '—',
                        uptime=safe_int(self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % onu_num)),
                        snmp_worker=self)
        except EasySNMPTimeoutError as e:
            raise EasySNMPTimeoutError(
                "%s (%s)" % (gettext('wait for a reply from the SNMP Timeout'), e)
            )

    def get_device_name(self):
        return self.get_item('.1.3.6.1.2.1.1.5.0')

    def uptime(self):
        up_timestamp = safe_int(self.get_item('.1.3.6.1.2.1.1.9.1.4.1'))
        tm = RuTimedelta(seconds=up_timestamp / 100)
        return tm

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # Olt has no require snmp info
        pass

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.db_instance
        return plain_ip_device_mon_template(device)

    def register_device(self, extra_data: Dict):
        pass

    def port_disable(self, port_num: int):
        # May be disabled
        raise NotImplementedError

    def port_enable(self, port_num: int):
        # May be enabled
        raise NotImplementedError
