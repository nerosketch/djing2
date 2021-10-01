from django.utils.translation import gettext_lazy as _
from devices.device_config.base_device_strategy import SNMPWorker
from devices.device_config.switch.eltex.general import EltexSwitch
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategyContext, PortType
from djing2.lib import safe_int

_DEVICE_UNIQUE_CODE = 13


class EltexMes5324A(EltexSwitch):
    description = _("Eltex MES5324A switch")
    tech_code = "eltex_mes5324a_sw"

    @staticmethod
    def build_port(snmp, i: int, n: int):
        speed = safe_int(snmp.get_item(".1.3.6.1.2.1.2.2.1.5.%d" % n))
        if speed == 0xffffffff:
            speed = 10000000000
        return PortType(
            num=i,
            name=snmp.get_item(".1.3.6.1.2.1.31.1.1.1.18.%d" % n),
            status=snmp.get_item(".1.3.6.1.2.1.2.2.1.7.%d" % n) == 1,
            mac=snmp.get_item(".1.3.6.1.2.1.2.2.1.6.%d" % n),
            uptime=snmp.get_item(".1.3.6.1.2.1.2.2.1.9.%d" % n),
            speed=speed,
        )

    def get_ports(self) -> tuple:
        dev = self.model_instance
        snmp = SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw))
        return tuple(self.build_port(snmp, i, i) for i in range(1, self.ports_len+1))


SwitchDeviceStrategyContext.add_device_type(_DEVICE_UNIQUE_CODE, EltexMes5324A)
