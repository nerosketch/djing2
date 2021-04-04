from typing import Any
from django.core.management.base import BaseCommand
from traf_stat.models import TrafficArchiveModel


class Command(BaseCommand):
    help = "Creating postgresql partitioning tables for storing all traffic archive"

    def handle(self, *args: Any, **options: Any):
        TrafficArchiveModel.create_db_partitions()
        self.stdout.write(self.style.SUCCESS("OK"))
