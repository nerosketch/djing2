from datetime import datetime

from customer_service.models import CustomerService
from .base import format_fname, ExportTree, SimpleExportTree
from sorm_export.serializers.customer_service_serializer import CustomerServiceIncrementalFormat
from sorm_export.serializers.service_serializer import ServiceIncrementalNomenclature
from sorm_export.models import ExportStampTypeEnum, CommunicationStandardChoices


class NomenclatureSimpleExportTree(SimpleExportTree):
    """
    Файл выгрузки номенклатуры, версия 1.
    В этом файле выгружаются все услуги, предоставляемые оператором своим абонентам - номенклатура-справочник.
    FIXME: Определиться нужно-ли выгружать названия тарифов.
     А пока выгружается "Высокоскоростной доступ в интернет".
    Да и вообще тут пока всё статично.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/service_list_v1_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.SERVICE_NOMENCLATURE

    def export(self, *args, **kwargs):
        dat = [{
            "service_id": 1,
            "mnemonic": "Интернет",
            "description": "Высокоскоростной доступ в интернет",
            "begin_time": datetime(2017, 1, 1, 0, 0).date(),
            "operator_type_id": CommunicationStandardChoices.ETHERNET.label,
        }]
        ser = ServiceIncrementalNomenclature(data=dat, many=True)
        ser.is_valid(raise_exception=True)
        return ser.data


class CustomerServiceExportTree(ExportTree[CustomerService]):
    """
    Файл выгрузки услуг по абонентам.
    В этом файле выгружаются все привязки услуг к абонентам.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/services_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return CustomerServiceIncrementalFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.SERVICE_CUSTOMER

    def get_item(self, cs: CustomerService, *args, **kwargs):
        # srv = cs.service
        if hasattr(cs, "customer"):
            return {
                # "service_id": srv.pk,
                "service_id": 1,
                "idents": cs.customer.pk,
                "parameter": "Услуга высокоскоростного доступа в интернет",  # srv.descr or str(srv),
                "begin_time": cs.start_time,
                # "end_time": cs.deadline,
            }
        else:
            return None


class ManualDataCustomerServiceSimpleExportTree(SimpleExportTree):
    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/services_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_type(cls) -> ExportStampTypeEnum:
        return ExportStampTypeEnum.SERVICE_CUSTOMER_MANUAL

    def export(self, *args, **kwargs):
        ser = CustomerServiceIncrementalFormat(many=True, *args, **kwargs)
        ser.is_valid(raise_exception=True)
        return ser.data
