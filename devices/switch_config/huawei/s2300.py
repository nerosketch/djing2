from django.utils.translation import gettext_lazy as _
from djing2.lib import safe_int
from ..eltex import EltexSwitch, EltexPort
from ..base import GeneratorOrTuple, DeviceImplementationError


class HuaweiS2300(EltexSwitch):
    description = _('Huawei switch')
    is_use_device_port = True
    has_attachable_to_customer = True
    tech_code = 'huawei_s2300'

    def get_ports(self) -> GeneratorOrTuple:
        # interfaces count
        # yield safe_int(self.get_item('.1.3.6.1.2.1.17.1.2.0'))

        interfaces_ids = self.get_list('.1.3.6.1.2.1.17.1.4.1.2')
        if interfaces_ids is None:
            raise DeviceImplementationError('Switch returned null')

        def build_port(i: int, n: int):
            speed = self.get_item('.1.3.6.1.2.1.2.2.1.5.%d' % n)
            oper_status = safe_int(self.get_item('.1.3.6.1.2.1.2.2.1.7.%d' % n)) == 1
            link_status = safe_int(self.get_item('.1.3.6.1.2.1.2.2.1.8.%d' % n)) == 1
            ep = EltexPort(
                dev_interface=self,
                num=i + 1,
                snmp_num=n,
                name=self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % n),  # name
                status=oper_status,  # status
                mac=b'',  # self.get_item('.1.3.6.1.2.1.2.2.1.6.%d' % n),    # mac
                speed=0 if not link_status else safe_int(speed),  # speed
                uptime=self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % n)  # UpTime
            )
            return ep

        return tuple(build_port(i, int(n)) for i, n in enumerate(interfaces_ids))
