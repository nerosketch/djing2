from .base import format_fname
from sorm_export.ftp_worker.func import send_file2ftp


store_fname = './apps/sorm_export/gateways.csv'


def export_gateways(event_time=None):
    send_file2ftp(
        fname=store_fname,
        remote_fname=f"ISP/dict/gateways_v1_{format_fname(event_time)}.txt"
    )
