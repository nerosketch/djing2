import os
from io import TextIOWrapper
from ftplib import FTP

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

DEFAULT_FTP_CREDENTIALS = getattr(settings, "DEFAULT_FTP_CREDENTIALS")
if DEFAULT_FTP_CREDENTIALS is None:
    raise ImproperlyConfigured("DEFAULT_FTP_CREDENTIALS not specified")


ftp_disable = os.environ.get("SORM_EXPORT_FTP_DISABLE", False)
ftp_disable = bool(ftp_disable)
ftp_host = DEFAULT_FTP_CREDENTIALS.get("host")
ftp_uname = DEFAULT_FTP_CREDENTIALS.get("uname")
ftp_passw = DEFAULT_FTP_CREDENTIALS.get("password")


def _ftp_credentials(fn):
    def _wrapper(*args, **kwargs):
        if ftp_disable:
            return fn(ftp=None, *args, **kwargs)
        with FTP(ftp_host) as ftp:
            ftp.login(ftp_uname, ftp_passw)
            return fn(ftp=ftp, *args, **kwargs)

    return _wrapper


@_ftp_credentials
def _send_buffer_as_file(fp: TextIOWrapper, remote_fname: str, _bin_mode=True, ftp=None) -> None:
    if ftp_disable:
        return
    if ftp is None:
        return
    if _bin_mode:
        ftp.storbinary("STOR %s" % remote_fname, fp)
    else:
        ftp.storlines("STOR %s" % remote_fname, fp)


def send_bin_buf2ftp(fp: TextIOWrapper, remote_fname: str) -> None:
    _send_buffer_as_file(fp=fp, remote_fname=remote_fname, _bin_mode=True)


def send_text_buf2ftp(fp: TextIOWrapper, remote_fname: str) -> None:
    _send_buffer_as_file(fp=fp, remote_fname=remote_fname, _bin_mode=False)


@_ftp_credentials
def send_file2ftp(fname: str, remote_fname: str, ftp=None) -> None:
    if ftp_disable:
        return
    with open(fname, "rb") as file:
        ftp.storbinary("STOR %s" % remote_fname, file)
