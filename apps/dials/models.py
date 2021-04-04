import os
from datetime import timedelta
from typing import Optional

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models
from djing2.lib import safe_int
from djing2.models import BaseAbstractModel
from profiles.models import UserProfile

DIAL_RECORDS_PATH = getattr(settings, "DIAL_RECORDS_PATH")
DIAL_RECORDS_EXTENSION = getattr(settings, "DIAL_RECORDS_EXTENSION")


class ATSDeviceModel(BaseAbstractModel):
    name = models.CharField(_("ATS device name"), max_length=32)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "ats_devices"
        ordering = ("-id",)


class DialAccount(UserProfile):
    ats_number = models.PositiveSmallIntegerField(_("ATS Number"), unique=True)

    class Meta:
        db_table = "ats_accounts"


# class DialLogQuerySet(models.QuerySet):
#     def create_dial(self, call: dict):
#         if not isinstance(call, dict):
#             raise TypeError
#
#         # Try to attach ats_dev to log instance
#         channel_name = call.get('channel_name')
#         # For example, channel name might be "Dongle/simname-0100000129"
#         if channel_name is not None and re.match('^[a-zA-Z]{1,12}\/.{1,32}\-\d{9,12}$', channel_name):
#             try:
#                 dev_type, call_detail = channel_name.split('/')
#                 dev_name, call_id = call_detail.split('-')
#                 ats_dev = ATSDeviceModel.objects.filter(name=dev_name).first()
#                 if ats_dev:
#                     call.update({
#                         'ats_dev': ats_dev
#                     })
#             except ValueError:
#                 pass
#
#         dclid = call.get('dst_caller_num')
#         if dclid is not None:
#             dacc = DialAccount.objects.filter(ats_number=dclid).first()
#             if dacc:
#                 call.update({
#                     'dial_account': dacc
#                 })
#
#         return self.create(**call)


class DialLog(BaseAbstractModel):
    uid = models.CharField(_("Unique identifier"), unique=True, max_length=32)
    caller_num = models.CharField(_("Caller number"), max_length=80, blank=True, null=True, default=None)
    caller_name = models.CharField(_("Caller name"), max_length=80, blank=True, null=True, default=None)
    dst_caller_num = models.CharField(_("Dst caller number"), max_length=80, blank=True, null=True, default=None)
    duration = models.PositiveSmallIntegerField(_("Duration"), default=0, help_text=_("Duration of the call"))
    billsec = models.PositiveSmallIntegerField(
        _("Talk time"), default=0, help_text=_("Duration of the call once it was answered")
    )
    create_time = models.DateTimeField(_("Start call time"))
    answer_time = models.DateTimeField(_("Answer time"))
    end_time = models.DateTimeField(_("End call time"), auto_now=True)
    ats_dev = models.ForeignKey(
        ATSDeviceModel, on_delete=models.CASCADE, verbose_name=_("ATS device"), blank=True, null=True, default=None
    )
    dial_account = models.ForeignKey(
        DialAccount,
        verbose_name=_("Account"),
        on_delete=models.SET_DEFAULT,
        blank=True,
        null=True,
        default=None,
        related_name="dials",
    )
    answered = models.BooleanField(_("Answered"), default=False)
    CALL_TYPES = (
        (0, _("Unknown")),
        (1, _("Incoming")),
        (2, _("Outgoing")),
    )
    call_type = models.PositiveSmallIntegerField(_("Call type"), choices=CALL_TYPES, default=0)

    call_killer = models.ForeignKey(
        DialAccount, verbose_name=_("Call killer"), on_delete=models.SET_DEFAULT, blank=True, null=True, default=None
    )

    # objects = DialLogQuerySet.as_manager()

    def get_dial_full_filename(self) -> Optional[str]:
        if self.answered:
            return os.path.join(DIAL_RECORDS_PATH, f"{self.uid}.{DIAL_RECORDS_EXTENSION}")
        # return '/var/spool/asterisk/monitor/1566997066.0.wav'

    def get_dial_fname(self) -> Optional[str]:
        if self.answered:
            return f"{self.uid}.{DIAL_RECORDS_EXTENSION}"

    def duration_humanity(self):
        secs = safe_int(self.duration)
        return timedelta(seconds=secs)

    def billsec_humanity(self):
        secs = safe_int(self.billsec)
        return timedelta(seconds=secs)

    def __str__(self):
        return self.uid

    class Meta:
        db_table = "dial_log"
        ordering = ("-id",)


class SMSModel(BaseAbstractModel):
    make_time = models.DateTimeField(_("Create time"), auto_now_add=True)
    sender = models.CharField(_("Sender"), max_length=80)
    receiver = models.CharField(_("Receiver"), max_length=80)
    text = models.CharField(_("Text"), max_length=280)

    def __str__(self):
        return self.text

    class Meta:
        db_table = "dial_sms"
        ordering = ("-id",)
