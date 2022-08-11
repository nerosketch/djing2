from django.db import models
from datetime import datetime
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class AsteriskCDR(models.Model):
    DISPOSITION_CHOICES = (
        ('NO ANSWER', _('No answer')),
        ('FAILED', _('Failed')),
        ('BUSY', _('Busy')),
        ('ANSWERED', _('Answered')),
        ('UNKNOWN', _('Unknown'))
    )
    calldate = models.DateTimeField(default='0000-00-00 00:00:00', primary_key=True)
    clid = models.CharField(max_length=80, default='')
    src = models.CharField(max_length=80, default='')
    dst = models.CharField(max_length=80, default='')
    dcontext = models.CharField(max_length=80, default='')
    channel = models.CharField(max_length=80, default='')
    dstchannel = models.CharField(max_length=80, default='')
    lastapp = models.CharField(max_length=80, default='')
    lastdata = models.CharField(max_length=80, default='')
    duration = models.IntegerField(default=0)
    billsec = models.IntegerField(default=0)
    disposition = models.CharField(max_length=45, choices=DISPOSITION_CHOICES, default='')
    amaflags = models.IntegerField(default=0)
    accountcode = models.CharField(max_length=20, default='')
    userfield = models.CharField(max_length=255, default='')
    uniqueid = models.CharField(max_length=32, unique=True)

    def save(self, *args, **kwargs):
        return

    def delete(self, *args, **kwargs):
        return

    def path_to_media(self):
        path = getattr(settings, 'DIALING_MEDIA', '/media')
        if self.userfield == 'request':
            return "%s/recording/request" % path
        elif self.userfield == 'report':
            return "%s/recording/bug" % path
        return "%s/monitor" % path

    def url(self):
        if type(self.calldate) is datetime:
            return "%s/%s-%s-%s.wav" % (
                self.path_to_media(), self.calldate.strftime('%Y/%m/%d/%H_%M'), self.src, self.dst
            )

    class Meta:
        db_table = 'cdr'
        managed = False
        ordering = ('-calldate',)


class SMSModel(models.Model):
    when = models.DateTimeField(auto_now_add=True)
    src = models.CharField(_('Source'), max_length=32)
    dst = models.CharField(_('Destination'), max_length=32)
    dev = models.CharField(max_length=20)
    text = models.CharField(max_length=255)
    SMS_OUT_STATUS = (
        ('nw', _('New')),
        ('st', _('Sent')),
        ('fd', _('Failed'))
    )
    status = models.CharField(_('Status'), max_length=2, choices=SMS_OUT_STATUS, default='nw')

    class Meta:
        db_table = 'sms'
        verbose_name = _('SMS')
        verbose_name_plural = _('SMS')
        ordering = ('-when',)

    def __str__(self):
        return self.text
