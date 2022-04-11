from typing import Iterable

from fin_app.models.alltime import AllTimePayLog, PayAllTimeGateway
from sorm_export.hier_export.base import iterable_export_decorator, format_fname
from sorm_export.serializers.payment import UnknownPaymentExportFormat


@iterable_export_decorator
def export_customer_unknown_payment(pays: Iterable[AllTimePayLog], event_time=None):
    """
    Файл выгрузки платежей версии 1.
    В этом файле выгружаются информация о платежах,
    совершённых абонентами. Выгрузка является потоковой,
    т.е. необходимо выгружать только новые события платежей
    за время, прошедшее с последней выгрузки.
    """
    def _gen(pay: AllTimePayLog):
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

    return UnknownPaymentExportFormat, _gen, pays, f"ISP/abonents/payments_v1_{format_fname(event_time)}.txt"
