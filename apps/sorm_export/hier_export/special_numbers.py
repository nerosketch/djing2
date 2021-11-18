from .base import format_fname
from sorm_export.ftp_worker.func import send_file2ftp

store_fname = './apps/sorm_export/special_numbers.csv'


def export_special_numbers(event_time=None):
    send_file2ftp(
        fname=store_fname,
        remote_fname=f"ISP/dict/special_numbers_{format_fname(event_time)}.txt"
    )
