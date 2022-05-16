from django.core.management.base import BaseCommand, no_translations
from sorm_export.models import ExportStampTypeEnum
from fin_app.models.alltime import AllTimePayLog
from sorm_export.hier_export.payment import CustomerUnknownPaymentExportTree


class Command(BaseCommand):
    help = "Exports all history customer payments"

    @no_translations
    def handle(self, *args, **options):
        pay_logs = AllTimePayLog.objects.exclude(customer=None).filter(
            customer__is_active=True
        )
        exporter = CustomerUnknownPaymentExportTree(recursive=False)
        data = exporter.export(queryset=pay_logs)
        exporter.upload2ftp(data=data, export_type=ExportStampTypeEnum.PAYMENT_UNKNOWN)
        self.stdout.write(self.style.SUCCESS("OK"))
