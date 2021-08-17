import re
import csv
from datetime import datetime
from django.core.management.base import BaseCommand, no_translations, CommandError

from sorm_export.hier_export.special_numbers import store_fname
from sorm_export.serializers.special_numbers import SpecialNumbersSerializerFormat
from sorm_export.hier_export.base import simple_export_decorator
from sorm_export.models import datetime_format


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


class Command(BaseCommand):
    help = "Creates or replaces"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    @no_translations
    def handle(self, add=None, show=False, rm=None, *args, **kwargs):
        if add is not None:
            self._add(add)
        elif show:
            self._show()
        elif rm is not None:
            self._rm(rm)
        else:
            self.stdout.write(self.style.ERROR('Unknown choice'))

    @staticmethod
    def _check_tel_unique(tel: str):
        try:
            with open(store_fname, 'r') as f:
                content = f.read()
            if tel in content:
                raise CommandError('Telephone "%s" already exists' % tel)
        except FileNotFoundError:
            with open(store_fname, 'w') as f:
                pass

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
                               "Detail: %s" % err)

    def _add(self, val):
        telephone_num, descr, start_time = self._split_args_data(val)
        self._check_tel_unique(telephone_num)
        data, fname = _make_special_number_data(
            tel_number=telephone_num,
            description=descr,
            start_time=start_time
        )
        with open(fname, 'a') as f:
            csv_writer = csv.writer(f, dialect="unix", delimiter=";")
            for row_data in data:
                row = (eld for elt, eld in row_data.items())
                csv_writer.writerow(row)
        self.stdout.write(self.style.SUCCESS('OK'))

    def _show(self):
        with open(store_fname, 'r') as f:
            content = f.read()
            print(content)

    def _rm(self, val):
        telephone_num = re.sub(r'\D', '', val)
        with open(store_fname, 'r') as f:
            csv_reader = csv.reader(f, dialect="unix", delimiter=";")
            filtered_lines = tuple(ln for ln in csv_reader if telephone_num not in ln)
        with open(store_fname, 'w') as f:
            csv_writer = csv.writer(f, dialect="unix", delimiter=";")
            for ln in filtered_lines:
                csv_writer.writerow(ln)

