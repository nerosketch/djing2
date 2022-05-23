import abc
from typing import Optional, TypeVar, Generic
from datetime import datetime

from django.db.models import QuerySet
from djing2.lib.logger import logger
from rest_framework.exceptions import ValidationError
from sorm_export.tasks.task_export import task_export
from sorm_export.models import ExportStampTypeEnum


T = TypeVar('T')

_fname_date_format = '%d%m%Y%H%M%S'


def format_fname(fname_timestamp: Optional[datetime] = None) -> str:
    if fname_timestamp is None:
        fname_timestamp = datetime.now()
    return fname_timestamp.strftime(_fname_date_format)


class ContinueIteration(Exception):
    pass


class ExportTree(Generic[T]):
    _recursive: bool
    _event_time: datetime
    _extra_kwargs: Optional[dict]
    parent_dependencies = ()

    def __init__(self, recursive=True, event_time: Optional[datetime]= None, extra_kwargs: Optional[dict] = None):
        self._recursive = recursive
        self._extra_kwargs = extra_kwargs
        if event_time is None:
            self._event_time = datetime.now()
        else:
            self._event_time = event_time

    def filter_queryset(self, queryset):
        return queryset

    @abc.abstractmethod
    def get_remote_ftp_file_name(self):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_export_format_serializer(cls):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_export_type(cls) -> ExportStampTypeEnum:
        raise NotImplementedError

    def get_items(self, queryset: QuerySet):
        for item in self.filter_queryset(queryset=queryset):
            try:
                r = self.get_item(item)
                # Добавляем или обновляем к результатам дополнительные данные.
                if isinstance(self._extra_kwargs, dict):
                    r.update(self._extra_kwargs)
                yield r

            except ContinueIteration:
                continue

    @abc.abstractmethod
    def get_item(self, *args, **kwargs):
        raise NotImplementedError

    #def _resolve_tree_deps(self, *args, **kwargs):
    #    """Экспортируем все зависимости рекурсивно"""
    #    raise NotImplementedError
    #    if not self._recursive:
    #        return self.export()
    #    for dep in self.parent_dependencies:
    #        return dep(*args, **kwargs)

    def export(self, queryset, *args, **kwargs):
        serializer_class = self.get_export_format_serializer()

        def _val_fn(dat):
            try:
                ser = serializer_class(data=dat)
                ser.is_valid(raise_exception=True)
                return ser.data
            except ValidationError as e:
                logger.error("%s | %s" % (e.detail, dat))

        gen = self.get_items(queryset=queryset, *args, **kwargs)

        res_data = (_val_fn(r) for r in gen if r)
        res_data = (r for r in res_data if r)

        return res_data

    def upload2ftp(self, data):
        fname = self.get_remote_ftp_file_name()
        task_export(data, fname, export_type=self.get_export_type())

    def exportNupload(self, *args, **kwargs):
        data = self.export(*args, **kwargs)
        self.upload2ftp(data=data)


class SimpleExportTree(ExportTree):
    def get_export_format_serializer(self):
        pass

    def export(self, *args, **kwargs) -> dict:
        raise NotImplementedError
