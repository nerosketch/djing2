import re
from datetime import datetime
from django.core.management.base import CommandError

from sorm_export.hier_export.special_numbers import store_fname
from sorm_export.serializers.special_numbers import SpecialNumbersSerializerFormat
from sorm_export.hier_export.base import simple_export_decorator
from sorm_export.models import datetime_format
from ._base_file_based_cmd import BaseFileBasedCommand


@simple_export_decorator
def _make_special_number_data(tel_number: str, description: str, start_time: datetime, event_time=None):
    dat = [{
        'tel_number': tel_number,
        # 'ip_address': '',
        'description': description,  # 'Телефон службы поддержки',
        'start_time': start_time,    # '29.01.2017T12:00:00',
        # 'end_time': ''
    }]

    ser = SpecialNumbersSerializerFormat(data=dat, many=True)
    return ser, store_fname


class Command(BaseFileBasedCommand):
    help = ("Creates or replaces special numbers: "
            "https://wiki.vasexperts.ru/doku.php?id="
            "sorm:sorm3:sorm3_subs_dump:sorm3_subs_special_numbers:start")
    store_fname = store_fname

    def add_arguments(self, parser):
        parser.add_argument(
            '--add', type=str, help="Add new special telephone number"
        )
        parser.add_argument(
            '--show', action='store_true', help="List available special telephone numbers"
        )
        parser.add_argument(
            '--rm', help="Remove special telephone number by number"
        )

    @staticmethod
    def _split_args_data(data: str):
        """Аргументы, разделённые запятой ','"""
        try:
            telephone_num, description, start_time = data.split(',')
            start_date = datetime.strptime(start_time.strip(), datetime_format)
            telephone_num = re.sub(r'\D', '', telephone_num)
            description = description.strip().replace('"', '').replace("'", '')
            return telephone_num, description, start_date
        except ValueError as err:
            raise CommandError("Arguments must be separated by comma. And check date format('DD.mm.YYYYTHH:MM:SS'). "
                               "Detail: %s" % err) from err

    def add(self, val):
        telephone_num, descr, start_time = self._split_args_data(val)
        self.check_unique(telephone_num)
        data, fname = _make_special_number_data(
            tel_number=telephone_num,
            description=descr,
            start_time=start_time
        )
        self.write2file(data)
        self.stdout.write(self.style.SUCCESS('OK'))

    def rm(self, val):
        telephone_num = re.sub(r'\D', '', val)
        self.del_from_file(telephone_num)
        self.stdout.write(self.style.SUCCESS('OK'))
