import csv
from datetime import datetime
from uwsgi_tasks import task
from sorm_export.serializers.aaa import AAAExportSerializer, AAA_EXPORT_FNAME


@task()
def save_radius_acct_start(event_time: datetime, data: AAAExportSerializer) -> None:
    line = [v for k, v in data.items()]
    with open(AAA_EXPORT_FNAME, "a") as f:
        csv_writer = csv.writer(f, dialect="unix", delimiter=";")
        csv_writer.writerow(line)
