from datetime import datetime

from customers.models import CustomerService
from .base import format_fname, ExportTree, SimpleExportTree
from ..models import CommunicationStandardChoices
from ..serializers.customer_service_serializer import CustomerServiceIncrementalFormat
from ..serializers.service_serializer import ServiceIncrementalNomenclature


class NomenclatureSimpleExportTree(SimpleExportTree):
    """
    Файл выгрузки номенклатуры, версия 1.
    В этом файле выгружаются все услуги, предоставляемые оператором своим абонентам - номенклатура-справочник.
    FIXME: Определиться нужно-ли выгружать названия тарифов.
     А пока выгружается "Высокоскоростной доступ в интернет".
    Да и вообще тут пока всё статично.
    """
    def get_export_format_serializer(self):
        return f"ISP/abonents/service_list_v1_{format_fname(self._event_time)}.txt"

    def export(self, *args, **kwargs):
        # def gen(srv: Service):
        #     return {
        #         "service_id": srv.pk,
        #         "mnemonic": str(srv.title)[:64],
        #         "description": str(srv.descr)[:256],
        #         "begin_time": srv.create_time.date(),  # дата начала будет датой создания тарифа.
        #         # end_time 36525 дней (~100 лет), типо бесконечно. Т.к. для вида услуги нет даты завершения,
        #         # как и нет даты окончания действия какого-то имени, например.
        #         "end_time": srv.create_time.date() + timedelta(days=36525),
        #         "operator_type_id": CommunicationStandardChoices.ETHERNET.label,
        #     }
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

    def get_export_format_serializer(self):
        return CustomerServiceIncrementalFormat

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

    def export(self, *args, **kwargs):
        ser = CustomerServiceIncrementalFormat(many=True, *args, **kwargs)
        ser.is_valid(raise_exception=True)
        return ser.data
