from typing import Iterable

from customers.models import CustomerService
from services.models import Service
from .base import exp_dec, format_fname
from ..models import CommunicationStandardChoices
from ..serializers.customer_service_serializer import CustomerServiceIncrementalFormat
from ..serializers.service_serializer import ServiceIncrementalNomenclature


@exp_dec
def export_nomenclature(services: Iterable[Service]):
    """
    Файл выгрузки номенклатуры, версия 1.
    В этом файле выгружаются все услуги, предоставляемые оператором своим абонентам - номенклатура-справочник.
    """
    def gen(srv: Service):
        return {
            'service_id': srv.pk,
            'mnemonic': str(srv.title)[:64],
            'description': str(srv.descr)[:256],
            'begin_time': '',  # FIXME: это не услуга для абонента, у неё нет начала, это общее описание услуги
            'operator_type_id': CommunicationStandardChoices.ETHERNET.name
        }
    res_data = map(gen, services)
    ser = ServiceIncrementalNomenclature(
        data=list(res_data), many=True
    )
    return ser, f'service_list_v1_{format_fname()}.txt'


@exp_dec
def export_customer_service(cservices: Iterable[CustomerService]):
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

    res_data = map(gen, cservices)
    ser = CustomerServiceIncrementalFormat(
        data=list(res_data), many=True
    )
    return ser, f'/home/cdr/ISP/abonents/services_{format_fname()}.txt'
    # return ser, f'services_{format_fname()}.txt'
