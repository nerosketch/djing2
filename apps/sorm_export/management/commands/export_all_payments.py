from datetime import datetime
from django.core.management.base import BaseCommand, no_translations
from sorm_export.tasks.task_export import task_export
from sorm_export.models import ExportStampTypeEnum
from fin_app.models.alltime import AllTimePayLog
from sorm_export.hier_export.payment import export_customer_unknown_payment


class Command(BaseCommand):
    help = "Exports all history customer payments"

    @no_translations
    def handle(self, *args, **options):
        pay_logs = AllTimePayLog.objects.exclude(customer=None).filter(
            customer__is_active=True
        )
        event_time = datetime.now()
        data, fname = export_customer_unknown_payment(pays=pay_logs, event_time=event_time)
        task_export(data, fname, ExportStampTypeEnum.PAYMENT_UNKNOWN)
        self.stdout.write(self.style.SUCCESS("OK"))
