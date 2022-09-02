from fin_app.models.alltime import AllTimePaymentLog, AllTimePayGateway
from sorm_export.hier_export.base import format_fname, ExportTree
from sorm_export.serializers.payment import UnknownPaymentExportFormat
from sorm_export.models import ExportStampTypeEnum


class CustomerUnknownPaymentExportTree(ExportTree[AllTimePaymentLog]):
    """
    Файл выгрузки платежей версии 1.
    В этом файле выгружаются информация о платежах,
    совершённых абонентами. Выгрузка является потоковой,
    т.е. необходимо выгружать только новые события платежей
    за время, прошедшее с последней выгрузки.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/payments_v1_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return UnknownPaymentExportFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.PAYMENT_UNKNOWN

    def get_item(self, pay: AllTimePaymentLog, *args, **kwargs):
        params = "платёжная система '%s', Идентификатор торговой точки: '%s'. Номер чека, выдаваемого клиенту: '%d'." % (
            AllTimePayGateway.pay_system_title,
            pay.trade_point,
            pay.receipt_num
        )
        return {
            "customer_id": pay.customer_id,
            "pay_time": pay.date_add,
            "amount": pay.amount,
            "pay_description": "Безналичный",  # TODO: Вынести это куда-то, чтоб были разные типы
            'pay_params': params
        }
