import os
import re
from typing import AnyStr, Iterable, Optional, Dict
from easysnmp import EasySNMPTimeoutError
from pexpect import TIMEOUT
from transliterate import translit
from django.utils.translation import gettext_lazy as _, gettext
from django.conf import settings

from djing2.lib import RuTimedelta, safe_int, safe_float
from devices.expect_scripts import (
    register_f601_onu, register_f660_onu,
    ExpectValidationError, OnuZteRegisterError,
    remove_from_olt_f601, register_f660v125s_onu
)
from devices.expect_scripts.base import sn_to_mac
from .base_intr import (
    DevBase, SNMPBaseWorker, BasePort, DeviceImplementationError,
    DeviceConfigurationError,
    GeneratorOrTuple
)


def _norm_name(name: str, replreg=None):
    if replreg is None:
        return re.sub(pattern='\W{1,255}', repl='', string=name, flags=re.IGNORECASE)
    return replreg.sub('', name)


def plain_ip_device_mon_template(device) -> Optional[AnyStr]:
    if not device:
        raise ValueError

    parent_host_name = _norm_name("%d%s" % (
        device.parent_dev.pk, translit(device.parent_dev.comment, language_code='ru', reversed=True)
    )) if device.parent_dev else None

    host_name = _norm_name("%d%s" % (device.pk, translit(device.comment, language_code='ru', reversed=True)))
    mac_addr = device.mac_addr
    r = (
        "define host{",
        "\tuse				generic-switch",
        "\thost_name		%s" % host_name,
        "\taddress			%s" % device.ip_address,
        "\tparents			%s" % parent_host_name if parent_host_name is not None else '',
        "\t_mac_addr		%s" % mac_addr if mac_addr is not None else '',
        "}\n"
    )
    return '\n'.join(i for i in r if i)


def ex_expect(filename, params=()):
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


class DLinkPort(BasePort):
    def __init__(self, snmp_worker, *args, **kwargs):
        super().__init__(writable=True, *args, **kwargs)
        if not issubclass(snmp_worker.__class__, SNMPBaseWorker):
            raise TypeError
        self.snmp_worker = snmp_worker


class DLinkDevice(DevBase, SNMPBaseWorker):
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
            return ex_expect('dlink_DGS1100_reboot.exp', (
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


class ONUdev(BasePort):
    def __init__(self, signal, snmp_worker, *args, **kwargs):
        super(ONUdev, self).__init__(*args, **kwargs)
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


class OLTDevice(DevBase, SNMPBaseWorker):
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
                    yield ONUdev(
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


class OnuDevice(DevBase, SNMPBaseWorker):
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
        host_name = _norm_name("%d%s" % (device.pk, translit(device.comment, language_code='ru', reversed=True)))
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
        pass

    def port_disable(self, port_num: int):
        pass

    def port_enable(self, port_num: int):
        pass


class EltexPort(BasePort):
    def __init__(self, snmp_worker, *args, **kwargs):
        BasePort.__init__(self, *args, **kwargs)
        if not issubclass(snmp_worker.__class__, SNMPBaseWorker):
            raise TypeError
        self.snmp_worker = snmp_worker


class EltexSwitch(DLinkDevice):
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


def conv_zte_signal(lvl: int) -> float:
    if lvl == 65535: return 0.0
    r = 0
    if 0 < lvl < 30000:
        r = lvl * 0.002 - 30
    elif 60000 < lvl < 65534:
        r = (lvl - 65534) * 0.002 - 30
    return round(r, 2)


class Olt_ZTE_C320(OLTDevice):
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


def _reg_dev_zte(device, extra_data: Dict, reg_func):
    if not extra_data:
        raise DeviceConfigurationError(_('You have not info in extra_data '
                                         'field, please fill it in JSON'))
    ip = None
    if device.ip_address:
        ip = device.ip_address
    elif device.parent_dev:
        ip = device.parent_dev.ip_address
    if ip:
        mac = str(device.mac_addr) if device.mac_addr else None

        # Format serial number from mac address
        # because saved mac address was make from serial number
        sn = "ZTEG%s" % ''.join('%.2X' % int(x, base=16) for x in mac.split(':')[-4:])
        telnet = extra_data.get('telnet')
        try:
            onu_snmp = reg_func(
                onu_mac=mac,
                serial=sn,
                zte_ip_addr=str(ip),
                telnet_login=telnet.get('login'),
                telnet_passw=telnet.get('password'),
                telnet_prompt=telnet.get('prompt'),
                onu_vlan=extra_data.get('default_vid')
            )
            if onu_snmp is not None:
                device.snmp_extra = onu_snmp
                device.save(update_fields=('snmp_extra',))
            else:
                raise DeviceConfigurationError('unregistered onu not found, sn=%s' % sn)
        except TIMEOUT as e:
            raise OnuZteRegisterError(e)
    else:
        raise DeviceConfigurationError('not have ip')


class ZteOnuDevice(OnuDevice):
    description = 'Zte ONU F660'
    tech_code = 'zte_onu'

    def get_details(self) -> Optional[Dict]:
        if self.db_instance is None:
            return
        snmp_extra = self.db_instance.snmp_extra
        if not snmp_extra:
            return

        fiber_num, onu_num = snmp_extra.split('.')
        fiber_num, onu_num = int(fiber_num), int(onu_num)
        fiber_addr = '%d.%d' % (fiber_num, onu_num)

        signal = safe_int(self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.10.%s.1' % fiber_addr))
        distance = self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.18.%s.1' % fiber_addr)

        sn = self.get_item('.1.3.6.1.4.1.3902.1012.3.28.1.1.5.%s' % fiber_addr)
        if sn is not None:
            sn = 'ZTEG%s' % ''.join('%.2X' % ord(x) for x in sn[-4:])

        status_map = {
            '1': 'ok',
            '2': 'down'
        }
        info = {
            'status': status_map.get(self.get_item('.1.3.6.1.4.1.3902.1012.3.50.12.1.1.1.%s.1' % fiber_addr), 'unknown'),
            'signal': conv_zte_signal(signal),
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
        device = self.db_instance
        if not device:
            return
        host_name = _norm_name("%d%s" % (device.pk, translit(device.comment, language_code='ru', reversed=True)))
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
        return _reg_dev_zte(self.db_instance, extra_data, register_f660_onu)

    def remove_from_olt(self, extra_data: Dict):
        dev = self.db_instance
        if not dev:
            return False
        if not dev.parent_dev or not dev.snmp_extra:
            return False
        telnet = extra_data.get('telnet')
        if not telnet:
            return False
        return remove_from_olt_f601(
            zte_ip_addr=str(dev.parent_dev.ip_address),
            telnet_login=telnet.get('login'),
            telnet_passw=telnet.get('password'),
            telnet_prompt=telnet.get('prompt'),
            snmp_info=str(dev.snmp_extra)
        )

    def get_fiber_str(self):
        dev = self.db_instance
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


class ZteF601(ZteOnuDevice):
    description = 'Zte ONU F601'

    def register_device(self, extra_data: Dict):
        return _reg_dev_zte(self.db_instance, extra_data, register_f601_onu)


class ZteF660v125s(ZteOnuDevice):
    description = 'ZTE ONU F660 V125 S'

    def register_device(self, extra_data: Dict):
        return _reg_dev_zte(self.db_instance, extra_data, register_f660v125s_onu)


class HuaweiSwitch(EltexSwitch):
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
            oper_status = safe_int(self.get_item('.1.3.6.1.2.1.2.2.1.7.%d' % n))
            oper_status = oper_status == 1
            link_status = safe_int(self.get_item('.1.3.6.1.2.1.2.2.1.8.%d' % n))
            link_status = link_status == 1
            ep = EltexPort(
                self,
                num=i + 1,
                snmp_num=n,
                name=self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % n),         # name
                status=oper_status,                                        # status
                mac='', # self.get_item('.1.3.6.1.2.1.2.2.1.6.%d' % n),    # mac
                speed=0 if not link_status else safe_int(speed),           # speed
                uptime=self.get_item('.1.3.6.1.2.1.2.2.1.9.%d' % n)        # UpTime
            )
            ep.writable = True
            return ep
        return tuple(build_port(i, int(n)) for i, n in enumerate(interfaces_ids))
