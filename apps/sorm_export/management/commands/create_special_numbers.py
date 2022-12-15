import re
from datetime import datetime
from django.core.management.base import CommandError, BaseCommand, no_translations

from sorm_export.models import datetime_format, SpecialNumbers


class Command(BaseCommand):
    help = ("Creates or replaces special numbers: "
            "https://wiki.vasexperts.ru/doku.php?id="
            "sorm:sorm3:sorm3_subs_dump:sorm3_subs_special_numbers:start")

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

    @no_translations
    def handle(self, add=None, show=False, rm=None, *args, **kwargs):
        if add:
            self.add(add)
        elif show:
            self.show()
        elif rm:
            self.rm(rm)
        else:
            self.stdout.write(self.style.ERROR('Unknown choice'))

    def add(self, val):
        telephone_num, descr, start_time = self._split_args_data(val)
        SpecialNumbers.objects.create(
            telephone=telephone_num,
            actual_begin_datetime=start_time,
            description=descr
        )
        self.stdout.write(self.style.SUCCESS('OK'))

    def rm(self, val):
        telephone_num = re.sub(r'\D', '', val)
        SpecialNumbers.objects.filter(telephone=telephone_num).delete()
        self.stdout.write(self.style.SUCCESS('OK'))

    def show(self):
        for sn in SpecialNumbers.objects.all():
            self.stdout.write(f"{sn.telephone}, {sn.actual_begin_datetime}, {sn.description or '-'}")
