import socket
from json import dumps
from django.conf import settings


def send_data(dat: dict, host: str = getattr(settings, 'WS_ADDR', '127.0.0.1:3211'), **kwargs) -> None:
    assert isinstance(dat, dict)
    assert bool(dat.get('eventType'))
    if kwargs:
        dat.update(kwargs)
    dat = dumps(dat)
    try:
        with socket.socket() as s:
            ipaddr, hport = host.split(':')
            s.connect((ipaddr, int(hport)))
            s.sendall(dat.encode())
    except ConnectionRefusedError:
        pass


__all__ = ['send_data']
