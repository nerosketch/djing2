from dataclasses import dataclass, asdict
from typing import Sequence
from django.core.mail import EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend
from djing2 import celery_app


@dataclass
class EmailMessageDataClass:
    from_email: str
    recipients: list[str]
    message: str
    subject: str = ''


@celery_app.task
def send_smtp_email_task(messages: list[dict]):
    msgs = (EmailMessageDataClass(**m) for m in messages)
    with EmailBackend() as conn:
        for msg in msgs:
            EmailMessage(
                subject=msg.subject,
                body=msg.message,
                from_email=msg.from_email,
                to=msg.recipients,
                connection=conn
            ).send()


class Djing2EmailBackend(BaseEmailBackend):
    """Email backend that send mails async."""

    def send_messages(self, email_messages: Sequence[EmailMessage]) -> int:
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0
        messages = [asdict(
            EmailMessageDataClass(
                from_email=message.from_email,
                recipients=message.recipients(),
                message=message.body,
                subject=message.subject,
            )
        ) for message in email_messages]

        send_smtp_email_task.delay(messages=messages)
        return len(messages)
