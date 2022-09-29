from typing import Optional, Type, overload
from netaddr import EUI
from djing2.lib import macbin2str, safe_int, LogicError

from radiusapp.vendor_specific import vendor_classes
from radiusapp.vendor_base import IVendorSpecific, SpeedInfoStruct, T, CustomerServiceLeaseResult


def parse_opt82(remote_id: bytes, circuit_id: bytes) -> tuple[Optional[EUI], int]:
    # 'remote_id': '0x000600ad24d0c544', 'circuit_id': '0x000400020002'
    mac, port = None, 0
    if not isinstance(remote_id, bytes):
        remote_id = bytes(remote_id)
    if not isinstance(circuit_id, bytes):
        circuit_id = bytes(circuit_id)

    if circuit_id.startswith(b"ZTE"):
        mac = remote_id.decode()
    elif circuit_id.startswith(b'0x48575443'):
        sn = int(circuit_id[2:], base=16).to_bytes(12, 'big')
        sn = sn[4:]
        mac = '54:43:%s' % b':'.join(sn[n:n + 2] for n in range(0, len(sn), 2)).decode()
        del sn
    else:
        try:
            port = safe_int(circuit_id[-1:][0])
        except IndexError:
            port = 0
        if len(remote_id) >= 6:
            mac = macbin2str(remote_id[-6:])
    return EUI(mac) if mac else None, port


class VendorManager:
    vendor_class: Optional[IVendorSpecific] = None

    def __init__(self, vendor_name: str):
        vc = [v for v in vendor_classes if v.vendor == vendor_name]
        if len(vc) == 1:
            self.vendor_class = vc[0]
        else:
            raise RuntimeError('Something went wrong in assigning vendor class')

    def get_opt82(self, data):
        if self.vendor_class:
            return self.vendor_class.parse_option82(data=data)

    @overload
    def get_rad_val(self, data, v: str, fabric_type: Type[T]) -> Optional[T]:
        ...

    @overload
    def get_rad_val(self, data, v: str, fabric_type: Type[T], default: T) -> T:
        ...

    def get_rad_val(self, data, v, fabric_type, default=None):
        if self.vendor_class:
            return self.vendor_class.get_rad_val(
                data=data,
                v=v,
                fabric_type=fabric_type,
                default=default
            )
        raise RuntimeError('Vendor class not specified')

    @staticmethod
    def build_dev_mac_by_opt82(agent_remote_id: str, agent_circuit_id: str) -> tuple[Optional[EUI], int]:
        def _cnv(v):
            return bytes.fromhex(v[2:]) if v.startswith("0x") else v.encode()

        agent_remote_id_b = _cnv(agent_remote_id)
        agent_circuit_id_b = _cnv(agent_circuit_id)

        dev_mac, dev_port = parse_opt82(agent_remote_id_b, agent_circuit_id_b)
        return dev_mac, dev_port

    def get_customer_mac(self, data) -> Optional[EUI]:
        if self.vendor_class:
            return self.vendor_class.get_customer_mac(data)

    def get_vlan_id(self, data):
        if self.vendor_class:
            return self.vendor_class.get_vlan_id(data)

    def get_service_vlan_id(self, data):
        if self.vendor_class:
            return self.vendor_class.get_service_vlan_id(data)

    def get_radius_username(self, data) -> Optional[str]:
        if self.vendor_class:
            return self.vendor_class.get_radius_username(data)

    def get_radius_unique_id(self, data):
        if self.vendor_class:
            return self.vendor_class.get_radius_unique_id(data)

    def get_speed(self, speed: SpeedInfoStruct) -> SpeedInfoStruct:
        if not self.vendor_class:
            raise RuntimeError('Vendor class not specified')
        return self.vendor_class.get_speed(speed=speed)

    def get_auth_session_response(
        self,
        db_result: CustomerServiceLeaseResult
    ) -> Optional[dict]:
        if self.vendor_class:
            return self.vendor_class.get_auth_session_response(
                db_result=db_result
            )

    def get_acct_status_type(self, request):
        if self.vendor_class:
            return self.vendor_class.get_acct_status_type(request)
        else:
            raise LogicError('Vendor class not instantiated')
