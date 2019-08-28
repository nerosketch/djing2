import os
from typing import Optional

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models

from .ami.call import DialChannel

DIAL_RECORDS_PATH = getattr(settings, 'DIAL_RECORDS_PATH')
DIAL_RECORDS_EXTENSION = getattr(settings, 'DIAL_RECORDS_EXTENSION')


def _join_call_log(c1: DialChannel):
    c2 = c1.linked_dial_channel
    if '+' in c1.caller_id_num:
        c = c1
    else:
        c = c2
    return {
        'uid': c.uid,
        'caller_num': c.caller_id_num,
        'caller_name': c.caller_id_name,
        'hold_time': c.hold_time,
        'talk_time': c.talk_time,
        'create_time': c.create_time,
        'answered': c.answered
    }


class ATSDeviceModel(models.Model):
    name = models.CharField(_('ATS device name'), max_length=32)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ats_devices'
        ordering = ('-id',)


class DialLogManager(models.Manager):
    def create_from_dial_channel(self, dial_channel: DialChannel):
        if not isinstance(dial_channel, DialChannel):
            raise TypeError
        hypothetical_ats_device = ATSDeviceModel.objects.filter(
            name__icontains=dial_channel.dev_name
        )
        create_params = _join_call_log(dial_channel)
        if hypothetical_ats_device.exists():
            create_params['ats_dev'] = hypothetical_ats_device.first()

        return self.create(**create_params)


class DialLog(models.Model):
    uid = models.FloatField(_('Unique identifier'), unique=True)
    caller_num = models.CharField(_('Caller number'), max_length=32, blank=True, null=True, default=None)
    caller_name = models.CharField(_('Caller name'), max_length=64, blank=True, null=True, default=None)
    hold_time = models.PositiveSmallIntegerField(_('Hold time'), default=0)
    talk_time = models.PositiveSmallIntegerField(_('Talk time'), default=0)
    create_time = models.DateTimeField(_('Start call time'), auto_now_add=True)
    end_time = models.DateTimeField(_('End call time'), auto_now_add=True)
    ats_dev = models.ForeignKey(
        ATSDeviceModel, on_delete=models.CASCADE,
        verbose_name=_('ATS device'), blank=True, null=True, default=None
    )
    answered = models.BooleanField(_('Answered'), default=False)

    def get_dial_full_filename(self) -> Optional[str]:
        if self.answered:
            return os.path.join(DIAL_RECORDS_PATH, '%s.%s' % (self.uid, DIAL_RECORDS_EXTENSION))
        # return '/var/spool/asterisk/monitor/1566997066.0.wav'

    def get_dial_fname(self) -> Optional[str]:
        if self.answered:
            return '%s.%s' % (self.uid, DIAL_RECORDS_EXTENSION)

    def __str__(self):
        return self.uid

    class Meta:
        db_table = 'dial_log'
        ordering = ('-id',)
