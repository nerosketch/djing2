from fin_app.models.alltime import AllTimePayLog, PayAllTimeGateway
from sorm_export.hier_export.base import format_fname, ExportTree
from sorm_export.serializers.payment import UnknownPaymentExportFormat


class CustomerUnknownPaymentExportTree(ExportTree[AllTimePayLog]):
    """
    Файл выгрузки платежей версии 1.
    В этом файле выгружаются информация о платежах,
    совершённых абонентами. Выгрузка является потоковой,
    т.е. необходимо выгружать только новые события платежей
    за время, прошедшее с последней выгрузки.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/abonents/payments_v1_{format_fname(self._event_time)}.txt"

    def get_export_format_serializer(self):
        return UnknownPaymentExportFormat

    def get_item(self, pay: AllTimePayLog, *args, **kwargs):
        params = "платёжная система '%s', Идентификатор торговой точки: '%s'. Номер чека, выдаваемого клиенту: '%d'." % (
            PayAllTimeGateway.pay_system_title,
            pay.trade_point,
            pay.receipt_num
        )
        return {
            "customer_id": pay.customer_id,
            "pay_time": pay.date_add,
            "amount": pay.sum,
            "pay_description": "Безналичный",  # TODO: Вынести это куда-то, чтоб были разные типы
            'pay_params': params
        }
