from uwsgi_tasks import task

from fin_app.models.alltime import AllTimePayLog
from sorm_export.hier_export.payment import CustomerUnknownPaymentExportTree
from sorm_export.models import ExportStampTypeEnum


@task()
def export_customer_payment_task(
    customer_id,
    pay_id,
    date_add,
    summ,
    trade_point,
    receipt_num,
    pay_gw,
    event_time=None
):
    pay_logs = (AllTimePayLog(
        customer_id=customer_id,
        pay_id=pay_id,
        date_add=date_add,
        sum=summ,
        trade_point=trade_point,
        receipt_num=receipt_num,
        pay_gw=pay_gw
    ),)
    exporter = CustomerUnknownPaymentExportTree(event_time=event_time)
    data = exporter.export(queryset=pay_logs)
    exporter.upload2ftp(data=data)

