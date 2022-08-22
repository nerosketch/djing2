from sorm_export.models import ExportStampModel, ExportStampTypeEnum, ExportStampStatusEnum
from uwsgi_tasks import cron

from djing2.lib.logger import logger
from fin_app.models.alltime import AllTimePaymentLog
from sorm_export.hier_export.payment import CustomerUnknownPaymentExportTree


@cron(minute=0, hour=1)
def export_customer_payments_periodic_task(signal_number):
    last_export_pay_row = ExportStampModel.objects.filter(
        export_type=ExportStampTypeEnum.PAYMENT_UNKNOWN,
        export_status=ExportStampStatusEnum.SUCCESSFUL
    ).only('last_attempt_time').order_by('-id').first()

    if last_export_pay_row is None:
        logger.warning("No one previews export stamp found. May be you don't yet exported payments.")
        return
    pay_logs = AllTimePaymentLog.objects.exclude(customer=None).filter(
        customer__is_active=True,
        date_add__gte=last_export_pay_row.last_attempt_time,
    )
    CustomerUnknownPaymentExportTree(recursive=False).exportNupload(queryset=pay_logs)
