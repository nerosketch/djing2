from enum import Enum
import socket
from json import dumps
from django.conf import settings


class WsEventTypeEnum(Enum):
    UPDATE_TASK = "updatetask"
    UPDATEPERMS = "updateperms"
    UPDATE_CUSTOMER_LEASES = "ucls"
    UPDATE_CUSTOMER = "update_customer"


class WebSocketSender:
    _sock = None

    def __init__(self, host=None):
        if host is None:
            host = getattr(settings, "WS_ADDR", "127.0.0.1:3211")
        ipaddr, hport = host.split(":")
        self._ipaddr, self._hport = ipaddr, int(hport)

    def __call__(self, dat: dict, host=None, **kwargs):
        assert isinstance(dat, dict)
        assert bool(dat.get("eventType"))

        if kwargs:
            dat.update(kwargs)
        dat = dumps(dat).encode()
        try:
            if self._sock is None:
                with socket.socket() as s:
                    s.connect((self._ipaddr, self._hport))
                    s.sendall(dat)
            else:
                self._sock.sendall(dat)
        except ConnectionRefusedError:
            pass

    def __enter__(self):
        try:
            self._sock = socket.socket()
            self._sock.connect((self._ipaddr, self._hport))
        except ConnectionRefusedError:
            self._sock.close()
            self._sock = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._sock:
            self._sock.close()


send_data2ws = WebSocketSender()
