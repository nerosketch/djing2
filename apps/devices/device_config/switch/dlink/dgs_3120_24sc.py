from typing import AnyStr, List, Generator
import struct

from djing2.lib import safe_int, RuTimedelta, process_lock
from devices.device_config.base_device_strategy import SNMPWorker
from devices.device_config.switch.switch_device_strategy import (
    SwitchDeviceStrategyContext, SwitchDeviceStrategy,
    PortType
)
from devices.device_config.base import (
    Vlans,
    Vlan,
    Macs,
    MacItem,
    DeviceImplementationError,
)


_DEVICE_UNIQUE_CODE = 9


class DlinkDGS_3120_24SCSwitchInterface(SwitchDeviceStrategy):
    """Dlink DGS-3120-24SC"""

    has_attachable_to_customer = False
    tech_code = "dlink_sw"
    description = "DLink DGS-3120-24SC"
    is_use_device_port = True
    ports_len = 24

    def read_port_vlan_info(self, port: int) -> Vlans:
        if port > self.ports_len or port < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)
        vid = 1
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        while True:
            member_ports, vid = snmp.get_next_keyval(".1.3.6.1.2.1.17.7.1.4.3.1.2.%d" % vid)
            if not member_ports:
                break
            if isinstance(member_ports, str):
                member_ports = member_ports.encode()
            vid = safe_int(vid)
            if vid in (0, 1):
                break
            member_ports = self._make_ports_map(member_ports[:4])
            if not member_ports[port - 1]:
                continue
            untagged_members = snmp.get_item("1.3.6.1.2.1.17.7.1.4.3.1.4.%d" % vid)
            untagged_members = self._make_ports_map(untagged_members[:4])
            name = self.get_vid_name(vid)
            yield Vlan(vid=vid, title=name, native=untagged_members[port - 1])

    @staticmethod
    def _make_ports_map(data: AnyStr) -> List[bool]:
        if isinstance(data, bytes):
            data = data[:4]
        else:
            raise DeviceImplementationError("data must be instance of bytes, %s got instead" % data.__class__)
        i = int.from_bytes(data, "big")
        return list(v == "1" for v in f"{i:032b}")

    @staticmethod
    def _make_buf_from_ports_map(ports_map: List) -> bytes:
        i = int("".join("1" if m else "0" for m in ports_map), base=2)
        return struct.pack("!I", i)

    def read_all_vlan_info(self) -> Vlans:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            vids = snmp.get_list_keyval(".1.3.6.1.2.1.17.7.1.4.3.1.1")
        for vid_name, vid in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            yield Vlan(vid=vid, title=vid_name)

    @process_lock()
    def read_mac_address_port(self, port_num: int) -> Macs:
        if port_num > self.ports_len or port_num < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            fdb = snmp.get_list_with_oid(".1.3.6.1.2.1.17.7.1.2.2.1.2")
            for fdb_port, oid in fdb:
                if port_num != int(fdb_port):
                    continue
                vid = safe_int(oid[-7:-6][0])
                fdb_mac = ":".join("%.2x" % int(i) for i in oid[-6:])
                vid_name = self.get_vid_name(vid)
                yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=safe_int(port_num))

    def read_mac_address_vlan(self, vid: int) -> Macs:
        vid = safe_int(vid)
        if vid > 4095 or vid < 1:
            raise DeviceImplementationError("VID must be in range 1-%d" % 4095)
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            fdb = snmp.get_list_with_oid(".1.3.6.1.2.1.17.7.1.2.2.1.2.%d" % vid)
            vid_name = self.get_vid_name(vid)
            for port_num, oid in fdb:
                fdb_mac = ":".join("%.2x" % int(i) for i in oid[-6:])
                yield MacItem(vid=vid, name=vid_name, mac=fdb_mac, port=safe_int(port_num))

    def _add_vlan_if_not_exists(self, vlan: Vlan) -> bool:
        """
        If vlan does not exsists on device, then create it
        :param vlan: vlan for check
        :return: True if vlan created
        """
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            snmp_vlan = snmp.get_item(".1.3.6.1.2.1.17.7.1.4.3.1.5.%d" % vlan.vid)
            if snmp_vlan is None:
                return self.create_vlan(vlan=vlan)
        return False

    def _toggle_vlan_on_port(self, vlan: Vlan, port: int, member: bool, request):
        if port > self.ports_len or port < 1:
            raise DeviceImplementationError("Port must be in range 1-%d" % self.ports_len)

        # if vlan does not exsists on device, then create it
        self._add_vlan_if_not_exists(vlan)

        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))

        port_member_tagged = snmp.get_item(".1.3.6.1.2.1.17.7.1.4.3.1.2.%d" % vlan.vid)
        port_member_untag = snmp.get_item(".1.3.6.1.2.1.17.7.1.4.3.1.4.%d" % vlan.vid)
        if not port_member_tagged or not port_member_untag:
            return False

        port_member_tagged_map = self._make_ports_map(port_member_tagged)
        port_member_untag_map = self._make_ports_map(port_member_untag)
        if member:
            port_member_untag_map[port - 1] = vlan.native
            port_member_tagged_map[port - 1] = True
        else:
            port_member_untag_map[port - 1] = False
            port_member_tagged_map[port - 1] = False

        port_member_tagged = self._make_buf_from_ports_map(port_member_tagged_map)
        port_member_untag = self._make_buf_from_ports_map(port_member_untag_map)

        return snmp.set_multiple(
            oid_values=[
                (".1.3.6.1.2.1.17.7.1.4.3.1.2.%d" % vlan.vid, port_member_tagged, "OCTETSTR"),
                (".1.3.6.1.2.1.17.7.1.4.3.1.4.%d" % vlan.vid, port_member_untag, "OCTETSTR"),
            ]
        )

    def get_ports(self) -> Generator:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            ifs_ids = snmp.get_list(".1.3.6.1.2.1.10.7.2.1.1")
            for num, if_id in enumerate(ifs_ids, 1):
                if num > self.ports_len:
                    return
                yield self.get_port(snmp_num=if_id)

    def get_port(self, snmp_num: int):
        snmp_num = safe_int(snmp_num)
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            status = snmp.get_item(".1.3.6.1.2.1.2.2.1.7.%d" % snmp_num)
            status = status and int(status) == 1
            return PortType(
                num=snmp_num,
                name=snmp.get_item(".1.3.6.1.2.1.31.1.1.1.18.%d" % snmp_num),
                status=status,
                mac=snmp.get_item(".1.3.6.1.2.1.2.2.1.6.%d" % snmp_num),
                speed=snmp.get_item(".1.3.6.1.2.1.2.2.1.5.%d" % snmp_num),
                uptime=int(snmp.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % snmp_num)),
            )

    def port_toggle(self, port_num: int, state: int):
        oid = "%s.%d" % (".1.3.6.1.2.1.2.2.1.7", port_num)
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            snmp.set_int_value(oid, state)

    def port_disable(self, port_num: int):
        self.port_toggle(port_num, 2)

    def port_enable(self, port_num: int):
        self.port_toggle(port_num, 1)

    def get_device_name(self):
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.get_item(".1.3.6.1.2.1.1.1.0")

    def get_uptime(self) -> str:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            uptimestamp = safe_int(snmp.get_item(".1.3.6.1.2.1.1.8.0"))
        tm = RuTimedelta(seconds=uptimestamp / 100)
        return str(tm)

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        # Dlink has no require snmp info
        pass


SwitchDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, DlinkDGS_3120_24SCSwitchInterface)
