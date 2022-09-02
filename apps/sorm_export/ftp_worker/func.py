from io import TextIOWrapper
from ftplib import FTP

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from sorm_export.models import ExportFailedStatus


def get_credentials():
    DEFAULT_FTP_CREDENTIALS = getattr(settings, "DEFAULT_FTP_CREDENTIALS")
    if DEFAULT_FTP_CREDENTIALS is None:
        raise ImproperlyConfigured("DEFAULT_FTP_CREDENTIALS not specified")
    return {
        'ftp_disable': bool(DEFAULT_FTP_CREDENTIALS.get("disabled", False)),
        'ftp_host': DEFAULT_FTP_CREDENTIALS.get("host"),
        'ftp_uname': DEFAULT_FTP_CREDENTIALS.get("uname"),
        'ftp_passw': DEFAULT_FTP_CREDENTIALS.get("password"),
        'ftp_port': DEFAULT_FTP_CREDENTIALS.get("port", 21)
    }


def _ftp_credentials(fn):
    def _wrapper(*args, **kwargs):
        cred = get_credentials()
        if cred['ftp_disable']:
            return fn(ftp=None, *args, **kwargs)
        ftp = FTP()
        try:
            ftp.connect(
                host=cred['ftp_host'],
                port=cred['ftp_port']
            )
            ftp.login(
                user=cred['ftp_uname'],
                passwd=cred['ftp_passw']
            )
            return fn(ftp=ftp, *args, **kwargs)
        finally:
            ftp.close()

    return _wrapper


@_ftp_credentials
def _send_buffer_as_file(fp: TextIOWrapper, remote_fname: str, _bin_mode=True, ftp=None) -> None:
    cred = get_credentials()
    if cred['ftp_disable']:
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
    cred = get_credentials()
    if cred['ftp_disable']:
        return
    try:
        with open(fname, "rb") as file:
            ftp.storbinary("STOR %s" % remote_fname, file)
    except FileNotFoundError as err:
        raise ExportFailedStatus(err) from err
