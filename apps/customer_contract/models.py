from datetime import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _
from djing2.models import BaseAbstractModel
from profiles.models import UserProfile
from customers.models import Customer
from customer_contract.custom_signals import finish_customer_contract_signal
from rest_framework.exceptions import ValidationError


def _datetime_now_time():
    return datetime.now()


class CustomerContractModel(BaseAbstractModel):
    """Customer contract info"""
    __before_is_active: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__before_is_active = bool(self.is_active)

    customer = models.ForeignKey(
        to=Customer,
        verbose_name=_('Customer'),
        on_delete=models.CASCADE,
    )
    start_service_time = models.DateTimeField(
        _('Start service time'),
        default=_datetime_now_time,
    )
    end_service_time = models.DateTimeField(
        _('End service time'),
        null=True, blank=True, default=None,
    )
    is_active = models.BooleanField(
        _('Is active'),
        default=True
    )
    contract_number = models.CharField(
        _('Contract number'),
        max_length=64,
        unique=True
    )
    title = models.CharField(
        _('Title'),
        max_length=64,
        null=True, blank=True, default=None,
    )
    note = models.CharField(
        _('Note'),
        max_length=512,
        null=True, blank=True, default=None,
    )
    extended_data = models.JSONField(
        _('Extended data'),
        null=True, blank=True, default=None,
    )

    def __str__(self):
        return self.contract_number

    def finish(self):
        self.is_active = False
        self.end_service_time = datetime.now()
        finish_customer_contract_signal.send(
            sender=self.__class__,
            instance=self
        )
        setattr(self, '__from_finish', True)
        self.save(update_fields=['is_active', 'end_service_time'])

    def save(self, *args, **kwargs):
        if not self.__before_is_active and bool(self.is_active):
            # prevent restore contract from inactive
            raise ValidationError(_('Restoring from inactive is not allowed'))
        if not hasattr(self, '__from_finish') and self.__before_is_active != self.is_active:
            # prevent directly change is_active field
            raise ValidationError(_('Direct change is_active is not allowed'))
        delattr(self, '__from_finish')
        return super().save(*args, **kwargs)

    class Meta:
        db_table = 'contract'


class CustomerContractAttachmentModel(BaseAbstractModel):
    """Document attachment for customer contract"""

    contract = models.ForeignKey(
        CustomerContractModel,
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_DEFAULT,
        null=True, blank=True, default=None,
    )
    title = models.CharField(max_length=64)
    doc_file = models.FileField(
        upload_to="contract_attachments/%Y/%m/",
        max_length=128
    )
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "contract_attachment"
