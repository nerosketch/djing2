from djing2.lib.logger import logger
from addresses.fias_socrbase import AddressFIASInfo
from addresses.models import AddressModel
from sorm_export.serializers import individual_entity_serializers
from sorm_export.models import ExportFailedStatus, ExportStampTypeEnum
from .base import format_fname, ExportTree, ContinueIteration


class AddressExportTree(ExportTree[AddressModel]):
    """
    Файл выгрузки адресных объектов.
    В этом файле выгружается иерархия адресных объектов, которые фигурируют
    в адресах прописки и точек подключения оборудования.
    За один вызов этой процедуры выгружается адресная
    инфа по одному адресному объекту. Чтобы выгрузить несколько адресных объектов -
    можно вызвать её в цикле.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/regions_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return individual_entity_serializers.AddressObjectFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.CUSTOMER_ADDRESS

    def get_items(self, queryset):
        for item in self.filter_queryset(queryset=queryset):
            try:
                yield self.get_item(item)
            except ContinueIteration:
                continue
            except ExportFailedStatus as err:
                logger.error("AddressExportTree error: %s" % str(err))

    def get_item(self, fias_addr: AddressModel, *args, **kwargs):
        addr = AddressFIASInfo.get_address(addr_code=fias_addr.fias_address_type)
        if addr is None:
            logger.error('Fias address with code %d not found' % fias_addr.fias_address_type)
            raise ContinueIteration

        return {
            "address_id": str(fias_addr.pk),
            "parent_id": str(fias_addr.parent_addr_id) if fias_addr.parent_addr_id else "",
            "type_id": fias_addr.fias_address_type,
            "region_type": addr.addr_short_name,
            "title": fias_addr.title,
            "full_title": fias_addr.full_title(),
        }

