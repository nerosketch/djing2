import re
from datetime import datetime

from bitfield import BitField
from django.conf import settings
from django.core import validators
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.signals import post_init, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext as _
from encrypted_model_fields.fields import EncryptedCharField

from djing2.lib import LogicError, safe_float
from gateways.nas_managers import (
    SubnetQueue, GatewayFailedResult,
    GatewayNetworkError
)
from profiles.models import BaseAccount, MyUserManager, UserProfile
from services.models import Service, PeriodicPay, OneShotPay
from groupapp.models import Group
from .customer import Customer


class CustomerIpLease(models.Model):
    ip_address = models.GenericIPAddressField(
        verbose_name=_('Ip address'),
        null=True,
        blank=True,
        default=None
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        verbose_name=_('Customer')
    )
