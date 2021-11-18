from typing import List
from django.core.management.base import BaseCommand, no_translations

from messenger.tasks import send_messenger_broadcast_message_task


class Command(BaseCommand):
    help = "Send test message to messenger chat bot"

    def add_arguments(self, parser):
        parser.add_argument("text", help="Message text", nargs=1, type=str)

    @no_translations
    def handle(self, text: List[str], *args, **options):
        text = text[0]
        send_messenger_broadcast_message_task(
            text=text
        )
        self.stdout.write(self.style.SUCCESS('OK'))
