from sorm_export.serializers import individual_entity_serializers
from .base import simple_export_decorator, format_fname
from ..models import FiasRecursiveAddressModel


@simple_export_decorator
def export_address_object(fias_addr: FiasRecursiveAddressModel, event_time=None):
    """
    Файл выгрузки адресных объектов.
    В этом файле выгружается иерархия адресных объектов, которые фигурируют
    в адресах прописки и точек подключения оборудования.
    За один вызов этой процедуры выгружается адресная
    инфа по одному адресному объекту. Чтобы выгрузить несколько адресных объектов -
    можно вызвать её в цикле.
    """

    dat = {
        "address_id": str(fias_addr.pk),
        "parent_id": str(fias_addr.parent_ao_id) if fias_addr.parent_ao_id is not None else "",
        "type_id": fias_addr.ao_type,
        "region_type": fias_addr.get_ao_type_display(),
        "title": fias_addr.title,
        "full_title": f"{fias_addr.get_ao_type_display()} {fias_addr.title}",
    }

    ser = individual_entity_serializers.AddressObjectFormat(data=dat)
    return ser, f"ISP/abonents/regions_{format_fname(event_time)}.txt"


def make_address_street_objects():
    """
    Тут формируется формат выгрузки улицы в дополение в выгрузкам адресных объектов.
    """
    streets = FiasRecursiveAddressModel.get_streets_as_addr_objects()
    for street in streets:
        # FIXME: расчитывать код улицы.
        # FIXME: street_id может пересекаться с FiasRecursiveAddressModel.pk т.к. это разные таблицы, со своими id
        street_id, parent_ao_id, parent_ao_type, street_name = street
        dat = {
            "address_id": str(street_id),
            "parent_id": str(parent_ao_id),
            "type_id": 6576,
            "region_type": "ул.",
            "title": street_name,
            "full_title": "ул. %s" % street_name,
        }
        ser = individual_entity_serializers.AddressObjectFormat(data=dat)
        ser.is_valid(raise_exception=True)
        yield ser.data
