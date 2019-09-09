import os
from datetime import timedelta
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models

from djing2.lib import safe_int
from .ami.call import DialChannel, join_call_log

DIAL_RECORDS_PATH = getattr(settings, 'DIAL_RECORDS_PATH')
DIAL_RECORDS_EXTENSION = getattr(settings, 'DIAL_RECORDS_EXTENSION')
UserProfile = get_user_model()


class ATSDeviceModel(models.Model):
    name = models.CharField(_('ATS device name'), max_length=32)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ats_devices'
        ordering = ('-id',)


class DialAccount(UserProfile):
    ats_number = models.PositiveSmallIntegerField(_('ATS Number'), unique=True)

    class Meta:
        db_table = 'ats_accounts'


class DialLogManager(models.Manager):
    def create_from_dial_channel(self, dial_channel: DialChannel):
        if not isinstance(dial_channel, DialChannel):
            raise TypeError
        if dial_channel.initiator:
            ci = dial_channel
            co = dial_channel.linked_dial_channel
        else:
            co = dial_channel
            ci = dial_channel.linked_dial_channel

        create_params = join_call_log(dial_channel)

        create_params['dst_caller_num'] = co.caller_id_num
        create_params['dst_caller_name'] = co.caller_id_name

        # Call direction
        if dial_channel.initiator:
            create_params['call_type'] = 2
        else:
            create_params['call_type'] = 1

        # Call device
        hypothetical_ats_device = ATSDeviceModel.objects.filter(
            name__icontains=ci.dev_name
        ).first()
        if hypothetical_ats_device:
            create_params['ats_dev'] = hypothetical_ats_device
        del hypothetical_ats_device

        # Employee account
        hypothetical_dial_account = DialAccount.objects.filter(
            ats_number=safe_int(ci.caller_id_num)
        ).first()
        if hypothetical_dial_account:
            create_params['dial_account'] = hypothetical_dial_account

        # Place dial killer. The one who hang up
        if ci.dial_killer:
            if hypothetical_dial_account:
                create_params['call_killer'] = hypothetical_dial_account
        elif co.dial_killer:
            hypothetical_dial_account = DialAccount.objects.filter(
                ats_number=safe_int(co.caller_id_num)
            ).first()
            if hypothetical_dial_account:
                create_params['call_killer'] = hypothetical_dial_account

        return self.create(**create_params)


class DialLog(models.Model):
    uid = models.CharField(_('Unique identifier'), unique=True, max_length=32)
    caller_num = models.CharField(_('Caller number'), max_length=80, blank=True, null=True, default=None)
    caller_name = models.CharField(_('Caller name'), max_length=80, blank=True, null=True, default=None)
    dst_caller_num = models.CharField(_('Dst caller number'), max_length=80, blank=True, null=True, default=None)
    dst_caller_name = models.CharField(_('Dst caller name'), max_length=80, blank=True, null=True, default=None)
    hold_time = models.PositiveSmallIntegerField(_('Hold time'), default=0)
    talk_time = models.PositiveSmallIntegerField(_('Talk time'), default=0)
    create_time = models.DateTimeField(_('Start call time'), auto_now_add=True)
    end_time = models.DateTimeField(_('End call time'), auto_now_add=True)
    ats_dev = models.ForeignKey(
        ATSDeviceModel, on_delete=models.CASCADE,
        verbose_name=_('ATS device'), blank=True, null=True, default=None
    )
    dial_account = models.ForeignKey(
        DialAccount, verbose_name=_('Account'),
        on_delete=models.SET_DEFAULT, blank=True,
        null=True, default=None, related_name='dials'
    )
    answered = models.BooleanField(_('Answered'), default=False)
    CALL_TYPES = (
        (0, _('Unknown')),
        (1, _('Incoming')),
        (2, _('Outgoing')),
    )
    call_type = models.PositiveSmallIntegerField(_('Call type'), choices=CALL_TYPES, default=0)

    call_killer = models.ForeignKey(
        DialAccount, verbose_name=_('Call killer'),
        on_delete=models.SET_DEFAULT, blank=True,
        null=True, default=None
    )

    objects = DialLogManager()

    def get_dial_full_filename(self) -> Optional[str]:
        if self.answered:
            return os.path.join(DIAL_RECORDS_PATH, '%s.%s' % (self.uid, DIAL_RECORDS_EXTENSION))
        # return '/var/spool/asterisk/monitor/1566997066.0.wav'

    def get_dial_fname(self) -> Optional[str]:
        if self.answered:
            return '%s.%s' % (self.uid, DIAL_RECORDS_EXTENSION)

    def hold_time_humanity(self):
        secs = safe_int(self.hold_time)
        return timedelta(seconds=secs)

    def talk_time_humanity(self):
        secs = safe_int(self.talk_time)
        return timedelta(seconds=secs)

    def __str__(self):
        return self.uid

    class Meta:
        db_table = 'dial_log'
        ordering = ('-id',)
