import os
import csv
from datetime import datetime
from djing2 import celery_app
from djing2.lib import locked_open
from sorm_export.serializers.aaa import AAA_EXPORT_FNAME
from sorm_export.ftp_worker.func import send_file2ftp
from sorm_export.hier_export.base import format_fname


def save_radius_acct(data: dict) -> None:
    line = [v for k, v in data.items()]
    with locked_open(AAA_EXPORT_FNAME, "a") as f:
        csv_writer = csv.writer(f, dialect="unix", delimiter=";")
        csv_writer.writerow(line)


@celery_app.task
def upload_aaa_2_ftp():
    try:
        if os.path.getsize(AAA_EXPORT_FNAME) > 0:
            now = datetime.now()
            send_file2ftp(
                fname=AAA_EXPORT_FNAME,
                remote_fname=f"ISP/aaa/aaa_v1_{format_fname(now)}.txt",
                clear=True
            )
    except FileNotFoundError:
        pass


celery_app.add_periodic_task(
    60*15,
    upload_aaa_2_ftp.s(),
    name='Upload aaa to ftp'
)
