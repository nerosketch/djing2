import abc
from typing import Optional, Tuple
from djing2.lib import macbin2str, safe_int

from radiusapp.vendor_specific import vendor_classes


def parse_opt82(remote_id: bytes, circuit_id: bytes) -> Tuple[Optional[str], int]:
    # 'remote_id': '0x000600ad24d0c544', 'circuit_id': '0x000400020002'
    mac, port = None, 0
    remote_id, circuit_id = bytes(remote_id), bytes(circuit_id)
    if circuit_id.startswith(b'ZTE'):
        mac = remote_id.decode()
    else:
        try:
            port = safe_int(circuit_id[-1:][0])
        except IndexError:
            port = 0
        if len(remote_id) >= 6:
            mac = macbin2str(remote_id[-6:])
    return mac, port


class IVendorSpecific(abc.ABC):
    @property
    @abc.abstractmethod
    def vendor(self):
        raise NotImplementedError

    @staticmethod
    def get_rad_val(data, v: str):
        k = data.get(v)
        if k:
            k = k.get('value')
            if k:
                return k[0]

    @abc.abstractmethod
    def parse_option82(self, data) -> Optional[Tuple[str, str]]:
        raise NotImplementedError


class VendorManager(object):
    vendor_class: Optional[IVendorSpecific] = None

    def __init__(self, vendor_name: str):
        vc = [v for v in vendor_classes if v.vendor == vendor_name]
        if len(vc) == 1:
            self.vendor_class = vc[0]

    def get_opt82(self, data):
        if self.vendor_class:
            return self.vendor_class.parse_option82(data=data)

    @staticmethod
    def build_dev_mac_by_opt82(agent_remote_id: str, agent_circuit_id: str):
        dig = int(agent_remote_id, base=16)
        agent_remote_id = dig.to_bytes((dig.bit_length() + 7) // 8, 'big')
        dig = int(agent_circuit_id, base=16)
        agent_circuit_id = dig.to_bytes((dig.bit_length() + 7) // 8, 'big')

        dev_mac, dev_port = parse_opt82(agent_remote_id, agent_circuit_id)
        return dev_mac, dev_port

