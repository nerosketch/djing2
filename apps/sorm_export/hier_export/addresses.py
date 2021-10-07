import logging

from addresses.fias_socrbase import AddressFIASInfo
from addresses.models import AddressModel
from sorm_export.serializers import individual_entity_serializers
from .base import simple_export_decorator, format_fname


def get_remote_export_filename(event_time=None) -> str:
    return f"ISP/abonents/regions_{format_fname(event_time)}.txt"


@simple_export_decorator
def export_address_object(fias_addr: AddressModel, event_time=None):
    """
    Файл выгрузки адресных объектов.
    В этом файле выгружается иерархия адресных объектов, которые фигурируют
    в адресах прописки и точек подключения оборудования.
    За один вызов этой процедуры выгружается адресная
    инфа по одному адресному объекту. Чтобы выгрузить несколько адресных объектов -
    можно вызвать её в цикле.
    """

    addr = AddressFIASInfo.get_address(addr_code=fias_addr.fias_address_type)
    if addr is None:
        logging.error('Fias address with code %d not found' % fias_addr.fias_address_type)
        return None, None

    dat = {
        "address_id": str(fias_addr.pk),
        "parent_id": str(fias_addr.parent_addr_id) if fias_addr.parent_addr_id is not None else "",
        "type_id": fias_addr.fias_address_type,
        "region_type": addr.addr_short_name,
        "title": fias_addr.title,
        "full_title": fias_addr.full_title(),
    }

    ser = individual_entity_serializers.AddressObjectFormat(data=dat)
    return ser, None
