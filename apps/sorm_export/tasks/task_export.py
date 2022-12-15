import csv
from io import StringIO
from sorm_export.ftp_worker.func import send_text_buf2ftp
from sorm_export.models import ExportStampTypeEnum


class Conv2BinStringIO(StringIO):
    def readline(self, *args, **kwargs):
        r = super().readline(*args, **kwargs)
        if isinstance(r, str):
            return r.encode()
        return r


# make export stamp for logging export
# end send data to ftp
def task_export(data, filename: str, export_type: ExportStampTypeEnum):
    if not data:
        return
    csv_buffer = Conv2BinStringIO()
    csv_writer = csv.writer(csv_buffer, dialect="unix", delimiter=";")
    num = None
    for num, row_data in enumerate(data):
        row = (eld for _, eld in row_data.items())
        csv_writer.writerow(row)
    csv_buffer.seek(0)
    if num is not None:
        send_text_buf2ftp(csv_buffer, filename)
    csv_buffer.close()
    del csv_buffer
