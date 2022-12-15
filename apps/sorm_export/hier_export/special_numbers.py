from sorm_export.models import SpecialNumbers, ExportStampTypeEnum
from sorm_export.tasks.task_export import task_export
from sorm_export.models import datetime_format
from .base import format_fname


def export_special_numbers(event_time=None):
    tels = ({
        'number': sn.telephone,
        'addr': None,
        'description': sn.description or 'Телефон службы поддержки',
        'actual_begin_datetime': sn.actual_begin_datetime.strftime(datetime_format),
        'actual_end_datetime': sn.ectual_end_datetime.strftime(datetime_format) if sn.ectual_end_datetime else None
    } for sn in SpecialNumbers.objects.all())
    task_export(
        data=tels,
        filename=f"ISP/dict/special_numbers_{format_fname(event_time)}.txt",
        export_type=ExportStampTypeEnum.SPECIAL_NUMBERS
    )
