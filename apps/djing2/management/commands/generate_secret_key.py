from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string


class Command(BaseCommand):
    help = "Generates SECRET_KEY"

    def handle(self, *args, **options):
        new_key = get_random_string(length=32)
        self.stdout.write(new_key)
