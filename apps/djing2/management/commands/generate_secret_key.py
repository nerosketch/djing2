from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string


class Command(BaseCommand):
    help = "Generates SECRET_KEY"

    def handle(self, *args, **options):
        secret_key = get_random_string(length=32)
        print("SECRET_KEY =", secret_key)
