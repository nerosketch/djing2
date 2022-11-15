import abc
import csv
from typing import Iterable
from contextlib import contextmanager
from django.core.management.base import BaseCommand, no_translations, CommandError


@contextmanager
def _ropen(fname: str, mode: str = 'r'):
    r = None
    try:
        r = open(fname, mode)
        yield r
    except FileNotFoundError:
        with open(fname, 'w'):
            pass
    finally:
        if r:
            r.close()


class BaseFileBasedCommand(BaseCommand):
    store_fname = None

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

    @abc.abstractmethod
    def add(self, val: str, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def rm(self, val: str, *args, **kwargs):
        raise NotImplementedError

    def check_unique(self, val: str, err_str='Line with "%s" already exists'):
        with _ropen(self.store_fname) as f:
            content = f.read()
        if val in content:
            raise CommandError(err_str % val)

    def write2file(self, data: Iterable[dict[str, str]]):
        with _ropen(self.store_fname, 'a') as f:
            csv_writer = csv.writer(f, dialect="unix", delimiter=";")
            for row_data in data:
                row = (eld for elt, eld in row_data.items())
                csv_writer.writerow(row)

    def del_from_file(self, val: str):
        with _ropen(self.store_fname) as f:
            csv_reader = csv.reader(f, dialect="unix", delimiter=";")
            filtered_lines = tuple(ln for ln in csv_reader if val not in ln)
        with open(self.store_fname, 'w') as f:
            csv_writer = csv.writer(f, dialect="unix", delimiter=";")
            for ln in filtered_lines:
                csv_writer.writerow(ln)

    def show(self):
        try:
            with _ropen(self.store_fname, 'r') as f:
                content = f.read()
            print(content, end='')
        except FileNotFoundError:
            pass
