from typing import Tuple, Optional
from djing2.lib import macbin2str, safe_int


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
