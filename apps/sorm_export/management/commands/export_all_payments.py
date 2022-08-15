from django.core.management.base import BaseCommand, no_translations
from fin_app.models.alltime import AllTimePaymentLog
from sorm_export.hier_export.payment import CustomerUnknownPaymentExportTree


class Command(BaseCommand):
    help = "Exports all history customer payments"

    @no_translations
    def handle(self, *args, **options):
        pay_logs = AllTimePaymentLog.objects.exclude(customer=None).filter(
            customer__is_active=True
        )
        CustomerUnknownPaymentExportTree(recursive=False).exportNupload(queryset=pay_logs)
        self.stdout.write(self.style.SUCCESS("OK"))
