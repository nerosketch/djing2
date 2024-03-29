from dataclasses import dataclass
from typing import Generator

from easysnmp import EasySNMPTimeoutError
from django.utils.translation import gettext_lazy as _

from devices.device_config.base_device_strategy import SNMPWorker
from djing2.lib import safe_int, RuTimedelta, safe_float, macbin2str
from ...base import Vlans, Vlan
from ...pon.pon_device_strategy import PonOltDeviceStrategy, PonOLTDeviceStrategyContext, FiberDataClass


@dataclass
class ONUdevPort:
    num: int
    name: str
    status: bool
    mac: str
    signal: float
    uptime: int
    fiberid: int


_DEVICE_UNIQUE_CODE = 2


@dataclass
class BdcomFiberDataClass(FiberDataClass):
    fb_active_onu: int


class BDCOM_P3310C(PonOltDeviceStrategy):
    has_attachable_to_customer = False
    description = "PON OLT"
    is_use_device_port = False
    ports_len = 4

    def scan_onu_list(self) -> Generator[ONUdevPort, None, None]:
        """
        If fast operation then just return tuple.
        If long operation then return the generator of ports count first,
        then max chunk size, and ports in next in generations
        """
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        # numbers
        # fiber_nums = (safe_int(i) for i in self.get_list('.1.3.6.1.4.1.3320.101.6.1.1.1'))
        # numbers
        fiber_onu_counts = snmp.get_list(".1.3.6.1.4.1.3320.101.6.1.1.2")

        # comma separated strings, remember to remove empty elements
        fiber_onu_id_nums = snmp.get_list_keyval(".1.3.6.1.4.1.3320.101.6.1.1.23")

        # All onu's count
        yield sum(safe_int(i) for i in fiber_onu_counts)

        # chunk max size
        yield 200

        try:
            for fiber_onu_num, fiber_id in fiber_onu_id_nums:
                for onu_num in fiber_onu_num.split(b","):
                    if not onu_num:
                        continue
                    onu_num = safe_int(onu_num)
                    if onu_num == 0:
                        continue
                    status = safe_int(snmp.get_item(".1.3.6.1.4.1.3320.101.10.1.1.26.%d" % onu_num))
                    signal = safe_float(snmp.get_item(".1.3.6.1.4.1.3320.101.10.5.1.5.%d" % onu_num))
                    mac = snmp.get(".1.3.6.1.4.1.3320.101.10.1.1.3.%d" % onu_num)
                    yield ONUdevPort(
                        num=onu_num,
                        name=snmp.get_item(".1.3.6.1.2.1.2.2.1.2.%d" % onu_num),
                        status=status == 3,
                        mac=macbin2str(mac.value),
                        signal=signal / 10 if signal else "—",
                        uptime=safe_int(snmp.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % onu_num)),
                        fiberid=safe_int(fiber_id),
                    )
        except EasySNMPTimeoutError as e:
            raise EasySNMPTimeoutError("{} ({})".format(_("wait for a reply from the SNMP Timeout"), e)) from e

    def get_fibers(self) -> tuple[BdcomFiberDataClass]:
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        fibers = tuple(
            BdcomFiberDataClass(
                fb_id=int(fiber_id),
                fb_name="EPON0/%d" % fiber_num,
                fb_active_onu=safe_int(snmp.get_item(".1.3.6.1.4.1.3320.101.6.1.1.21.%d" % int(fiber_id))),
                # 'fb_onu_ids': tuple(int(i) for i in self.get_item_plain(
                #     '.1.3.6.1.4.1.3320.101.6.1.1.23.%d' % int(fiber_id)).split(',') if i
                # ),
                fb_onu_num=safe_int(registered_onu_count),
            )
            for fiber_num, (registered_onu_count, fiber_id) in enumerate(
                snmp.get_list_keyval(".1.3.6.1.4.1.3320.101.6.1.1.2"), 1
            )
        )
        return fibers

    def get_device_name(self):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.get_item(".1.3.6.1.2.1.1.5.0")

    def get_uptime(self) -> RuTimedelta:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            up_timestamp = safe_int(snmp.get_item(".1.3.6.1.2.1.1.9.1.4.1"))
            tm = RuTimedelta(seconds=up_timestamp / 100)
            return tm

    def validate_extra_snmp_info(self, v: str) -> None:
        # Olt has no require snmp info
        pass

    def read_all_vlan_info(self) -> Vlans:
        yield Vlan(vid=1, title='Default')

    #############################
    #      Telnet access
    #############################

    # def login(self, login: str, password: str, *args, **kwargs) -> bool:
    #     orig_prompt = self.prompt
    #     self.prompt = b'>'
    #     r = super().login(
    #         login_prompt=b'Username:',
    #         login=login,
    #         password_prompt=b'Password:',
    #         password=password
    #     )
    #     self.prompt = orig_prompt
    #     self.write('enable')
    #     self.read_until(orig_prompt)
    #     return r

    # def _disable_prompt(self) -> None:
    #     self.write('terminal length 0')
    #     self.read_until(self.prompt)

    # def read_port_vlan_info(self, port: int) -> Vlans:
    #     self.write('show vlan int EPON0/%d' % port)
    #     out = self.read_until(self.prompt)
    #     for line in out.split(b'\n'):
    #         chunks = line.split()
    #         chlen = len(chunks)
    #         try:
    #             if chlen == 5:
    #                 vlans = chunks[3].decode()
    #             elif chlen == 1:
    #                 vlans = chunks[0].decode()
    #             else:
    #                 continue
    #             for i in vlans.split(','):
    #                 yield Vlan(int(i), title=None)
    #         except (ValueError, IndexError):
    #             pass

    # def read_all_vlan_info(self) -> Vlans:
    #     self.write('show vlan')
    #     out = self.read_until(self.prompt)
    #     for line in out.split(b'\n'):
    #         chunks = line.split()
    #         vid = chunks[0].decode()
    #         if not vid.isnumeric():
    #             continue
    #         try:
    #             vname = chunks[2].decode()
    #             yield Vlan(int(vid), vname)
    #         except (ValueError, IndexError):
    #             pass

    # def read_mac_address_port(self, port_num: int) -> Macs:
    #     self.write('show mac addr int EPON0/%d' % port_num)
    #     out = self.read_until(self.prompt)
    #     for line in out.split(b'\n'):
    #         chunks = line.split()
    #         if len(chunks) != 4:
    #             continue
    #         try:
    #             vid = int(chunks[0])
    #             mac = EUI(chunks[1].decode())
    #             stack_num, port = chunks[3].split(b':')
    #             yield MacItem(vid=vid, name=None, mac=mac, port=safe_int(port))
    #         except (ValueError, IndexError):
    #             pass

    # def read_mac_address_vlan(self, vid: int) -> Macs:
    #     self.write('show mac addr vlan %d' % vid)
    #     out = self.read_until(self.prompt)
    #     for line in out.split(b'\n'):
    #         chunks = line.split()
    #         if len(chunks) != 4:
    #             continue
    #         try:
    #             vlan_id = int(chunks[0])
    #             assert vid == vlan_id, 'Catch vid(%d) that is not equal to passed vid(%d)' % (
    #                 vlan_id, vid
    #             )
    #             mac = EUI(chunks[1].decode())
    #             stack, port = chunks[3].split(b':')
    #             yield MacItem(vid=vid, name=None, mac=mac, port=safe_int(port))
    #         except (ValueError, IndexError):
    #             pass

    # def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
    #     return self.attach_vlan_to_eport(vid, port, tag)

    # def attach_vlan_to_eport(self, vid: int, port: int, tag: bool = True) -> bool:
    #     if port > self.ports_len or port < 1:
    #         raise ValueError('Port must be in range 1-%d' % self.ports_len)
    #     self.write('conf')
    #     self.read_until('_config#')
    #     self.write('int EPON0/%d' % port)
    #     self.read_until('_epon0/%d#' % port)
    #     if tag:
    #         self.write('switch trunk vlan-allowed add %d' % vid)
    #     else:
    #         self.write('switchport trunk vlan-untagged %d' % vid)
    #     self.read_until('_epon0/%d#' % port)
    #     self._exit_fiber()
    #     self.write('exit')
    #     self.read_until(self.prompt)
    #     return True

    # def attach_vlan_to_gport(self, vids: Iterable[int], port: int, tag: bool = True) -> bool:
    #     if port > self.ports_len or port < 1:
    #         raise ValueError('Port must be in range 1-%d' % self.ports_len)
    #     self.write('conf')
    #     self.read_until('_config#')
    #     self.write('int g0/%d' % port)
    #     self.read_until('_g0/%d#' % port)
    #     for vid in vids:
    #         if tag:
    #             self.write('switch trunk vlan-allowed add %d' % vid)
    #             self.read_until('_g0/%d#' % port)
    #         else:
    #             self.write('switchport trunk vlan-untagged %d' % vid)
    #             break
    #     self.read_until('_g0/%d#' % port)
    #     self._exit_fiber()
    #     self.write('exit')
    #     self.read_until(self.prompt)
    #     return True

    # def attach_vlans_to_uplink(self, vlans: Vlans, port: int, tag: bool = True) -> None:
    #     self.attach_vlan_to_gport(vids, port, tag)

    # def _enter_fiber(self, fiber_num: int):
    #     self.write('conf')
    #     self.read_until('_config#')
    #     self.write('int EPON0/%d' % fiber_num)
    #     self.read_until('_epon0/%d#' % fiber_num)

    # def _exit_fiber(self):
    #     self.write('exit')
    #     self.read_until('_config#')

    # def detach_onu_sec(self, fiber_num: int, onu_nums: Iterable[int]) -> bool:
    #     self._enter_fiber(fiber_num)
    #     for onu_num in onu_nums:
    #         self.write('no epon bind-onu sequence %d' % onu_num)
    #         self.read_until('_epon0/%d#' % fiber_num)
    #     self._exit_fiber()
    #     return True

    # def detach_onu_mac(self, fiber_num: int, onu_macs: Macs) -> bool:
    #     self._enter_fiber(fiber_num)
    #     for mac in onu_macs:
    #         bdcom_mac = EUI(mac, dialect=mac_cisco)
    #         self.write('no epon bind-onu mac %s' % bdcom_mac)
    #         self.read_until('_epon0/%d#' % fiber_num)
    #     self._exit_fiber()
    #     return True


# class OLT_BDCOM_P33C_ONU:
#     def __init__(self, bt: BDCOM_P3310C, fiber_num: int, onu_num: int):
#         self.bt: BDCOM_P3310C = bt
#         self.fiber_num = fiber_num
#         self.onu_num = onu_num

    # def __enter__(self):
    #     self.bt.write('int EPON0/%d:%d' % (self.fiber_num, self.onu_num))
    #     self._read_until_onu_int()
    #     self.bt.write('epon onu all-port loopback detect')
    #     self._read_until_onu_int()

    # def _read_until_onu_int(self) -> bytes:
    #     return self.bt.read_until('_epon0/%d:%d#' % (self.fiber_num, self.onu_num))

    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     self.bt._exit_fiber()

    # def get_onu_cooper_state(self, port: int = 1) -> bool:
    #     self.bt.write('show epon int EPON0/%d:%d onu port %d state' % (
    #         self.fiber_num, self.onu_num, port
    #     ))
    #     out = self._read_until_onu_int()
    #     return b'Link-Up' in out

    # def attach_native_vlan(self, vid: int) -> None:
    #     self.bt.write('epon onu all-port ctc vlan mode tag %d' % vid)
    #     self._read_until_onu_int()

    # def attach_vlans(self, native_vid: int, tag_vlans: Vlans) -> None:
    #     tag_vids = ','.join(str(v.vid) for v in tag_vlans)
    #     self.bt.write('epon onu all-port ctc vlan mode trunk %d %s' % (
    #         native_vid, tag_vids
    #     ))
    #     self._read_until_onu_int()

PonOLTDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, BDCOM_P3310C)
