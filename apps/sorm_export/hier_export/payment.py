from typing import Iterable

from fin_app.models import AllTimePayLog
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
    dat = [{
        'customer_id': pay.customer_id,
        'pay_time': pay.date_add,
        'amount': pay.sum,
        'pay_description': 'Безналичный',  # TODO: Можно-ли указывать какой это платёж
        # 'pay_params': lease.mac_address
    } for pay in pays]

    ser = UnknownPaymentExportFormat(
        data=dat, many=True
    )
    return ser, f'ISP/abonents/payments_v1_{format_fname(event_time)}.txt'
