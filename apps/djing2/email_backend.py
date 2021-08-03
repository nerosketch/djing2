from dataclasses import dataclass, asdict
from typing import List
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from uwsgi_tasks import task


@dataclass
class EmailMessageDataClass:
    from_email: str
    recipients: List[str]
    message: str
    subject: str = ''


@task()
def _send_smtp_email_task(messages: List[dict]):
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


class Djing2EmailBackend(EmailBackend):
    """Email backend that send mails async."""

    def send_messages(self, email_messages: List[EmailMessage]) -> int:
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
                message=message.message(),
                subject=message.subject,
            )
        ) for message in email_messages]

        _send_smtp_email_task(messages=messages)
        return len(messages)
