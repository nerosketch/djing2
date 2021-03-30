from enum import Enum
import socket
from json import dumps
from django.conf import settings


class WsEventTypeEnum(Enum):
    UPDATE_TASK = "updatetask"
    UPDATEPERMS = "updateperms"
    UPDATE_CUSTOMER_LEASES = "ucls"
    UPDATE_CUSTOMER = "update_customer"


def send_data2ws(dat: dict, host: str = getattr(settings, "WS_ADDR", "127.0.0.1:3211"), **kwargs) -> None:
    assert isinstance(dat, dict)
    assert bool(dat.get("eventType"))
    if kwargs:
        dat.update(kwargs)
    dat = dumps(dat)
    try:
        with socket.socket() as s:
            ipaddr, hport = host.split(":")
            s.connect((ipaddr, int(hport)))
            s.sendall(dat.encode())
    except ConnectionRefusedError:
        pass
