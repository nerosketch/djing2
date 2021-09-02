from django.utils.translation import gettext_lazy as _

from djing2.lib import safe_int
from ..switch_device_strategy import SwitchDeviceStrategyContext
from ..eltex.general import EltexSwitch
from devices.device_config.base import DeviceImplementationError, Vlan, Vlans, Macs, MacItem
from ..switch_device_strategy import PortType
from ...base_device_strategy import SNMPWorker


class HuaweiS2300(EltexSwitch):
    description = _("Huawei switch")
    is_use_device_port = True
    has_attachable_to_customer = True
    tech_code = "huawei_s2300"
    ports_len = 26

    def get_ports(self) -> tuple:
        # interfaces count
        # yield safe_int(self.get_item('.1.3.6.1.2.1.17.1.2.0'))

        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))

        interfaces_ids = snmp.get_list(".1.3.6.1.2.1.17.1.4.1.2")
        if interfaces_ids is None:
            raise DeviceImplementationError("Switch returned null")
        interfaces_ids = tuple(next(interfaces_ids) for _ in range(self.ports_len))

        def build_port(i: int, n: int):
            speed = snmp.get_item(".1.3.6.1.2.1.2.2.1.5.%d" % n)
            oper_status = safe_int(snmp.get_item(".1.3.6.1.2.1.2.2.1.7.%d" % n)) == 1
            link_status = safe_int(snmp.get_item(".1.3.6.1.2.1.2.2.1.8.%d" % n)) == 1
            ep = PortType(
                model_instance=dev,
                num=i + 1,
                snmp_num=n,
                name=snmp.get_item(".1.3.6.1.2.1.2.2.1.2.%d" % n),  # name
                status=oper_status,  # status
                mac=b"",  # self.get_item('.1.3.6.1.2.1.2.2.1.6.%d' % n),    # mac
                speed=0 if not link_status else safe_int(speed),  # speed
                uptime=snmp.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % n),  # UpTime
            )
            return ep

        return tuple(build_port(i, int(n)) for i, n in enumerate(interfaces_ids))

    def read_all_vlan_info(self) -> Vlans:
        vid = 1
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        while True:
            res = snmp.get_next(".1.3.6.1.2.1.17.7.1.4.3.1.1.%d" % vid)
            vid = safe_int(res.value[5:])
            if vid == 1:
                continue
            if vid == 0:
                return
            yield Vlan(vid=vid, title=res.value)

    def read_mac_address_port(self, port_num: int) -> Macs:
        yield MacItem(vid=None, name="", mac="0:0:0:0:0:0", port=0)
        # first_port_index = safe_int(self.get_next('.1.3.6.1.2.1.17.1.4.1.2').value)
        # if first_port_index == 0:
        #     return
        # mac_oid = ''
        # snmp_port_id = True
        # while snmp_port_id:
        #     res = self.get_next('.1.3.6.1.2.1.17.4.3.1.2.%s' % mac_oid)
        #     if res.snmp_type != 'INTEGER':
        #         break
        #     snmp_port_id = safe_int(res.value)
        #     if snmp_port_id == 0:
        #         break
        #     real_port_num = snmp_port_id - first_port_index
        #     # print('real_port_num - port_num:', real_port_num, port_num)
        #     # if real_port_num != port_num:
        #     #     continue
        #     oid = [i for i in res.oid.split('.') if i]
        #     mac_oid = oid[-6:]
        #     mac = EUI(':'.join(f'{int(i):0x}' for i in mac_oid))
        #     port_name = self.get_item('.1.3.6.1.2.1.2.2.1.2.%d' % snmp_port_id)
        #     yield MacItem(vid=None, name=port_name, mac=str(mac), port=real_port_num+1)

    def read_port_vlan_info(self, port: int) -> Vlans:
        if port > self.ports_len or port < 1:
            raise ValueError("Port must be in range 1-%d" % self.ports_len)
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        vids = snmp.get_list_keyval(".1.3.6.1.2.1.17.7.1.4.3.1.1")
        for vid_name, vid in vids:
            vid = safe_int(vid)
            if vid in (0, 1):
                continue
            member_ports = snmp.get_item(".1.3.6.1.2.1.17.7.1.4.3.1.2.%d" % vid)
            if not member_ports:
                return
            member_ports = self._make_ports_map(member_ports[:4])
            if not member_ports[port]:
                # if port num is not <port>
                continue
            name = self.get_vid_name(vid)
            yield Vlan(vid=vid, title=name)


class HuaweiS5300_10P_LI_AC(HuaweiS2300):
    ports_len = 10
    tech_code = "huawei_s5300"
    description = _("Huawei switch S5300")
    is_use_device_port = True
    has_attachable_to_customer = True


SwitchDeviceStrategyContext.add_device_type(8, HuaweiS2300)
SwitchDeviceStrategyContext.add_device_type(12, HuaweiS5300_10P_LI_AC)
