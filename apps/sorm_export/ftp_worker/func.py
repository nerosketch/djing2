from io import TextIOWrapper
from ftplib import FTP

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DEFAULT_FTP_CREDENTIALS = getattr(settings, 'DEFAULT_FTP_CREDENTIALS')
if DEFAULT_FTP_CREDENTIALS is None:
    raise ImproperlyConfigured('DEFAULT_FTP_CREDENTIALS not specified')


def _send_file(fp: TextIOWrapper, remote_fname: str, _bin_mode=True) -> None:
    host = DEFAULT_FTP_CREDENTIALS.get('host')
    uname = DEFAULT_FTP_CREDENTIALS.get('uname')
    passw = DEFAULT_FTP_CREDENTIALS.get('password')
    with FTP(host) as ftp:
        ftp.login(uname, passw)
        if _bin_mode:
            ftp.storbinary('STOR %s' % remote_fname, fp)
        else:
            ftp.storlines('STOR %s' % remote_fname, fp)


def send_bin_file(fp: TextIOWrapper, remote_fname: str) -> None:
    _send_file(fp, remote_fname, True)


def send_text_file(fp: TextIOWrapper, remote_fname: str) -> None:
    _send_file(fp, remote_fname, False)
