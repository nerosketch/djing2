import csv
from datetime import datetime
from uwsgi_tasks import task, cron
from sorm_export.serializers.aaa import AAAExportSerializer, AAA_EXPORT_FNAME
from sorm_export.ftp_worker.func import send_file2ftp
from sorm_export.hier_export.base import format_fname


@task()
def save_radius_acct(event_time: datetime, data: AAAExportSerializer) -> None:
    line = [v for k, v in data.items()]
    with open(AAA_EXPORT_FNAME, "a") as f:
        csv_writer = csv.writer(f, dialect="unix", delimiter=";")
        csv_writer.writerow(line)


@cron(minute=-15)
def upload_aaa_2_ftp(signal_number):
    now = datetime.now()
    send_file2ftp(fname=AAA_EXPORT_FNAME, remote_fname=f"ISP/aaa/aaa_v1_{format_fname(now)}.txt")

    # Erase all content
    open(AAA_EXPORT_FNAME, 'w').close()
