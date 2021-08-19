from typing import Iterable

from fin_app.models.alltime import AllTimePayLog
from sorm_export.hier_export.base import simple_export_decorator, format_fname
from sorm_export.serializers.payment import UnknownPaymentExportFormat


@simple_export_decorator
def export_customer_unknown_payment(pays: Iterable[AllTimePayLog], event_time=None):
    """
    Файл выгрузки платежей версии 1.
    В этом файле выгружаются информация о платежах,
    совершённых абонентами. Выгрузка является потоковой,
    т.е. необходимо выгружать только новые события платежей
    за время, прошедшее с последней выгрузки.
    """
    def _build_pay_params(pay: AllTimePayLog) -> str:
        return 'Идентификатор торговой точки: "%s". Номер чека, выдаваемого клиенту: "%d".' % (
            pay.trade_point,
            pay.receipt_num
        )

    dat = [
        {
            "customer_id": pay.customer_id,
            "pay_time": pay.date_add,
            "amount": pay.sum,
            "pay_description": "Безналичный",  # TODO: Вынести это куда-то, чтоб были разные типы
            'pay_params': _build_pay_params(pay)
        }
        for pay in pays
    ]

    ser = UnknownPaymentExportFormat(data=dat, many=True)
    return ser, f"ISP/abonents/payments_v1_{format_fname(event_time)}.txt"
