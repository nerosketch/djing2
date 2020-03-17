import socket
from json import dumps
from django.conf import settings


def send_data(dat: dict, host: str = getattr(settings, 'WS_ADDR', '127.0.0.1:3211')) -> None:
    dat = dumps(dat)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(host)
        s.sendall(dat.encode())


__all__ = ['send_data']
