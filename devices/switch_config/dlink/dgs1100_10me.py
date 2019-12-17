import os
from typing import Optional, Dict
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from djing2.lib import safe_int, RuTimedelta
from ..base import DevBase, DeviceConfigurationError, GeneratorOrTuple, BasePort
from ..snmp_util import SNMPBaseWorker
from ..utils import plain_ip_device_mon_template


class DLinkPort(BasePort):
    def __init__(self, snmp_worker, *args, **kwargs):
        super().__init__(writable=True, *args, **kwargs)
        if not issubclass(snmp_worker.__class__, SNMPBaseWorker):
            raise TypeError
        self.snmp_worker = snmp_worker


def _ex_expect(filename, params=()):
    base_dir = getattr(settings, 'BASE_DIR')
    if base_dir is not None:
        exec_file = os.path.join(base_dir, 'devices', 'expect_scripts', filename)
        if os.path.isfile(exec_file) and os.access(path=exec_file, mode=os.X_OK):
            params = ' '.join(str(p) for p in params)
            if params:
                return os.system('%s %s' % (exec_file, params))
            else:
                return os.system(exec_file)
        else:
            raise DeviceConfigurationError(_('File %(filename)s is not exists or not executable') % {
                'filename': exec_file
            })


class DlinkDGS1100_10ME(DevBase, SNMPBaseWorker):
    has_attachable_to_customer = True
    tech_code = 'dlink_sw'
    description = _('DLink switch')
    is_use_device_port = True

    def __init__(self, dev_instance):
        DevBase.__init__(self, dev_instance)
        SNMPBaseWorker.__init__(self, dev_instance.ip_address, dev_instance.man_passw, 2)

    def reboot(self, save_before_reboot=False):
        dat = self.db_instance.extra_data
        if dat is None:
            raise DeviceConfigurationError(
                _('You have not info in extra_data '
                  'field, please fill it in JSON')
            )
        login = dat.get('login')
        passw = dat.get('password')
        if login and passw:
            return _ex_expect('dlink_DGS1100_reboot.exp', (
                self.db_instance.ip_address,
                login, passw,
                1 if save_before_reboot else 0
            )), None

    def get_ports(self) -> GeneratorOrTuple:
        ifs_ids = self.get_list('.1.3.6.1.2.1.10.7.2.1.1')
        return tuple(self.get_port(snmp_num=if_id) for if_id in ifs_ids)

    def get_port(self, snmp_num: int):
        snmp_num = safe_int(snmp_num)
        status = self.get_item('.1.3.6.1.2.1.2.2.1.7.%d' % snmp_num)
        status = status and int(status) == 1
        return DLinkPort(
            num=snmp_num,
            name=self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % snmp_num),
            status=status,
            mac=self.get_item('.1.3.6.1.2.1.2.2.1.6.%d' % snmp_num),
            speed=self.get_item('.1.3.6.1.2.1.2.2.1.5.%d' % snmp_num),
            uptime=self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % snmp_num),
            snmp_worker=self
        )

    def port_disable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num), 2
        )

    def port_enable(self, port_num: int):
        self.set_int_value(
            "%s.%d" % ('.1.3.6.1.2.1.2.2.1.7', port_num), 1
        )

    def get_device_name(self):
        return self.get_item('.1.3.6.1.2.1.1.1.0')

    def uptime(self) -> str:
        uptimestamp = safe_int(self.get_item('.1.3.6.1.2.1.1.8.0'))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return str(tm)

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # Dlink has no require snmp info
        pass

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        device = self.db_instance
        return plain_ip_device_mon_template(device)

    def register_device(self, extra_data: Dict):
        pass
