from typing import List
from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend

from djing2.tasks import send_email_task


class Djing2EmailBackend(BaseEmailBackend):
    """Backend only send email task for uwsgi_tasks."""

    def send_messages(self, email_messages: List[EmailMessage]) -> int:
        if not email_messages:
            return 0

        r = 0
        for m in email_messages:
            send_email_task(
                subject=m.subject,
                message=m.body,
                from_email=m.from_email,
                recipient_list=m.to
            )
            r += 1
        return r
