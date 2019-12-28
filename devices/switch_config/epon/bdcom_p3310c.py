from typing import Optional, Dict
from easysnmp import EasySNMPTimeoutError
from django.utils.translation import gettext
from netaddr import EUI

from djing2.lib import safe_int, RuTimedelta, safe_float
from ..utils import plain_ip_device_mon_template
from ..base import DevBase, BasePort, GeneratorOrTuple, SNMPBaseWorker, Vlans, Vlan, Macs, MacItem


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


class BDCOM_P3310C(DevBase):
    has_attachable_to_customer = False
    description = 'PON OLT'
    is_use_device_port = False
    ports_len = 4

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

    def login(self, login: str, password: str, *args, **kwargs) -> bool:
        orig_prompt = self.prompt
        self.prompt = b'>'
        r = super().login(
            login_prompt=b'Username:',
            login=login,
            password_prompt=b'Password:',
            password=password
        )
        self.prompt = orig_prompt
        self.write('enable')
        self.read_until(orig_prompt)
        return r

    def _disable_prompt(self) -> None:
        self.write('terminal length 0')
        self.read_until(self.prompt)

    def read_port_vlan_info(self, port: int) -> Vlans:
        self.write('show vlan int EPON0/%d' % port)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            chlen = len(chunks)
            try:
                if chlen == 5:
                    vlans = chunks[3].decode()
                elif chlen == 1:
                    vlans = chunks[0].decode()
                else:
                    continue
                for i in vlans.split(','):
                    yield Vlan(int(i), name=None)
            except (ValueError, IndexError):
                pass

    def read_all_vlan_info(self) -> Vlans:
        self.write('show vlan')
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            vid = chunks[0].decode()
            if not vid.isnumeric():
                continue
            try:
                vname = chunks[2].decode()
                yield Vlan(int(vid), vname)
            except (ValueError, IndexError):
                pass

    def read_mac_address_port(self, port_num: int) -> Macs:
        self.write('show mac addr int EPON0/%d' % port_num)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) != 4:
                continue
            try:
                vid = int(chunks[0])
                mac = EUI(chunks[1].decode())
                stack_num, port = chunks[3].split(b':')
                yield MacItem(vid=vid, name=None, mac=mac, port=safe_int(port))
            except (ValueError, IndexError):
                pass

    def read_mac_address_vlan(self, vid: int) -> Macs:
        self.write('show mac addr vlan %d' % vid)
        out = self.read_until(self.prompt)
        for line in out.split(b'\n'):
            chunks = line.split()
            if len(chunks) != 4:
                continue
            try:
                vlan_id = int(chunks[0])
                assert vid == vlan_id, 'Catch vid(%d) that is not equal to passed vid(%d)' % (
                    vlan_id, vid
                )
                mac = EUI(chunks[1].decode())
                stack, port = chunks[3].split(b':')
                yield MacItem(vid=vid, name=None, mac=mac, port=safe_int(port))
            except (ValueError, IndexError):
                pass

    def create_vlans(self, vlan_list: Vlans) -> bool:
        self.write('conf')
        self.read_until('_config#')
        for vlan in vlan_list:
            self.write('vlan %d' % vlan.vid)
            self.read_until('config_vlan%d#' % vlan.vid)
            self.write('name %s' % self._normalize_name(vlan.name))
            self.read_until('config_vlan%d#' % vlan.vid)
            self.write('ex')
            self.read_until('_config#')
        self.write('exit')
        self.read_until(self.prompt)
        return True

    def delete_vlans(self, vlan_list: Vlans) -> bool:
        self.write('conf')
        self.read_until('_config#')
        for vlan in vlan_list:
            self.write('no vlan %d' % vlan.vid)
            res = self.read_until('_config#')
            if b'OK!' not in res:
                return False
        self.write('exit')
        self.read_until(self.prompt)
        return True

    def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
        self.write('conf')
        self.read_until('_config#')
        self.write('int EPON0/%d' % port)
        self.read_until('_epon0/%d#' % port)
        self.write('switch trunk vlan-allowed add %d' % vid)
        self.read_until('_epon0/%d#' % port)
        self.write('exit')
        self.read_until('_config#')
        self.write('exit')
        self.read_until(self.prompt)
        return True

    def detach_vlan_from_port(self, vid: int, port: int) -> bool:
        self.write('conf')
        self.read_until('_config#')
        self.write('int EPON0/%d' % port)
        self.read_until('_epon0/%d#' % port)
        self.write('switch trunk vlan-allowed remove %d' % vid)
        self.read_until('_epon0/%d#' % port)
        self.write('exit')
        self.read_until('_config#')
        self.write('exit')
        self.read_until(self.prompt)
        return True
