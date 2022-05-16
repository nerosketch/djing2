import abc
from typing import Optional, TypeVar, Generic
from datetime import datetime
from functools import wraps

from django.db.models import QuerySet
from djing2.lib.logger import logger
from rest_framework.exceptions import ValidationError
from sorm_export.tasks.task_export import task_export
from sorm_export.models import ExportStampTypeEnum


T = TypeVar('T')

_fname_date_format = '%d%m%Y%H%M%S'


def format_fname(fname_timestamp=None) -> str:
    if fname_timestamp is None:
        fname_timestamp = datetime.now()
    return fname_timestamp.strftime(_fname_date_format)


def simple_export_decorator(fn):
    @wraps(fn)
    def _wrapped(event_time=None, *args, **kwargs):
        if event_time is None:
            event_time = datetime.now()
        elif isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)
        ser, fname = fn(event_time=event_time, *args, **kwargs)
        ser.is_valid(raise_exception=True)
        return ser.data, fname
    return _wrapped


class ContinueIteration(Exception):
    pass


class ExportTree(Generic[T]):
    _recursive: bool
    _event_time: datetime
    parent_dependencies = ()

    def __init__(self, recursive=True, event_time: Optional[datetime]= None):
        self._recursive = recursive
        if event_time is None:
            self._event_time = datetime.now()
        else:
            self._event_time = event_time


    @abc.abstractmethod
    def get_remote_ftp_file_name(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_export_format_serializer(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_items(self, queryset: QuerySet, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def get_item(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def get_queryset(self):
        raise NotImplementedError

    #def _resolve_tree_deps(self, *args, **kwargs):
    #    """Экспортируем все зависимости рекурсивно"""
    #    raise NotImplementedError
    #    if not self._recursive:
    #        return self.export()
    #    for dep in self.parent_dependencies:
    #        return dep(*args, **kwargs)

    def export(self, queryset, event_time: Optional[datetime] = None, *args, **kwargs):
        if event_time is None:
            event_time = datetime.now()
        elif isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        serializer_class = self.get_export_format_serializer()

        def _val_fn(dat):
            try:
                ser = serializer_class(data=dat)
                ser.is_valid(raise_exception=True)
                return ser.data
            except ValidationError as e:
                logger.error("%s | %s" % (e.detail, dat))

        gen = self.get_items(event_time=event_time, queryset=queryset, *args, **kwargs)

        res_data = (_val_fn(r) for r in gen if r)
        res_data = (r for r in res_data if r)

        return res_data

    def upload2ftp(self, data, export_type: ExportStampTypeEnum):
        fname = self.get_remote_ftp_file_name()
        task_export(data, fname, export_type)

