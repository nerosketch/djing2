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
    # em = ExportStampModel.objects.create(
    #    data=data,
    #    export_status=ExportStampStatusEnum.NOT_EXPORTED,
    #    export_type=export_type
    # )
    # try:
    csv_buffer = Conv2BinStringIO()
    csv_writer = csv.writer(csv_buffer, dialect="unix", delimiter=";")
    num = 0
    for num, row_data in enumerate(data):
        row = (eld for elt, eld in row_data.items())
        csv_writer.writerow(row)
    csv_buffer.seek(0)
    if num > 0:
        send_text_buf2ftp(csv_buffer, filename)
    csv_buffer.close()
    del csv_buffer
    #    em.attempts_count = 1
    #    em.last_attempt_time = datetime.now()
    #    em.export_status = ExportStampStatusEnum.SUCCESSFUL
    #    em.save(update_fields=['attempts_count', 'last_attempt_time', 'export_status'])
    # except all_errors:
    #    em.export_status = ExportStampStatusEnum.FAILED
    #    em.save(update_fields=['export_status'])
