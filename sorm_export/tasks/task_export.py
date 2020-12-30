import csv
from io import StringIO
from sorm_export.ftp_worker.func import send_text_file


class _Conv2BinStringIO(StringIO):
    def readline(self, *args, **kwargs):
        r = super().readline(*args, **kwargs)
        if isinstance(r, str):
            return r.encode()
        return r


def task_export(data, filename: str):
    csv_buffer = _Conv2BinStringIO()
    csv_writer = csv.writer(csv_buffer, dialect='unix')
    for row_data in data:
        row = (eld for elt, eld in row_data.items())
        csv_writer.writerow(row)
    csv_buffer.seek(0)
    send_text_file(csv_buffer, filename)
