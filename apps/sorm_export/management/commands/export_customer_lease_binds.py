from django.core.management.base import BaseCommand, no_translations

from sorm_export.management.commands._general_func import export_customer_lease_binds


class Command(BaseCommand):
    help = "Export customer ip lease binds"

    @no_translations
    def handle(self, *args, **options):
        export_customer_lease_binds()
        self.stdout.write(self.style.SUCCESS("OK"))
