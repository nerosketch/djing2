from typing import Iterable

from customers.models import CustomerService
from services.models import Service
from .base import iterable_export_decorator, format_fname
from ..models import CommunicationStandardChoices
from ..serializers.customer_service_serializer import CustomerServiceIncrementalFormat
from ..serializers.service_serializer import ServiceIncrementalNomenclature


@iterable_export_decorator
def export_nomenclature(services: Iterable[Service], event_time=None):
    """
    Файл выгрузки номенклатуры, версия 1.
    В этом файле выгружаются все услуги, предоставляемые оператором своим абонентам - номенклатура-справочник.
    """
    def gen(srv: Service):
        return {
            'service_id': srv.pk,
            'mnemonic': str(srv.title)[:64],
            'description': str(srv.descr)[:256],
            'begin_time': srv.create_time.date(),  # дата начала будет датой создания тарифа.
                                                   # TODO: end_time нужно заполнять.
            'operator_type_id': CommunicationStandardChoices.ETHERNET
        }

    return (
        ServiceIncrementalNomenclature, gen, services,
        f'/home/cdr/ISP/abonents/service_list_v1_{format_fname(event_time)}.txt'
    )


@iterable_export_decorator
def export_customer_service(cservices: Iterable[CustomerService], event_time=None):
    """
    Файл выгрузки услуг по абонентам.
    В этом файле выгружаются все привязки услуг к абонентам.
    """
    def gen(cs: CustomerService):
        srv = cs.service
        return {
            'service_id': srv.pk,
            'idents': cs.customer.pk,
            'parameter': srv.descr,
            'begin_time': cs.start_time,
            'end_time': cs.deadline
        }

    return (
        CustomerServiceIncrementalFormat, gen, cservices,
        f'/home/cdr/ISP/abonents/services_{format_fname(event_time)}.txt'
    )
