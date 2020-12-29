from django.utils.translation import gettext as _
from django.db import models

date_format = '%d.%m.%Y'
datetime_format = '%d.%m.%YT%H:%M:%S'


class ExportStampStatusEnum(models.IntegerChoices):
    NOT_EXPORTED = 0, _('Not exported')
    SUCCESSFUL = 1, _('Successful')
    FAILED = 2, _('Failed')
    IN_PROGRESS = 3, _('In progress')


class ExportStampModel(models.Model):
    first_attempt_time = models.DateTimeField(_('Action time'), auto_now_add=True)
    last_attempt_time = models.DateTimeField(_('Last attempt time'), auto_now_add=True)
    attempts_count = models.IntegerField(_('Attempt count'), default=0)
    export_status = models.PositiveIntegerField(
        _('Export status'),
        choices=ExportStampStatusEnum.choices,
        default=ExportStampStatusEnum.NOT_EXPORTED
    )

    class Meta:
        db_table = 'sorm_export_stamp'


class CommunicationStandardChoices(models.IntegerChoices):
    NOT_CONCRETE = 0, _('Not concrete')
    GSM = 1, 'GSM'
    CDMA = 2, 'CDMA'
    PSTN = 3, _('PSTN')  # ТФоП сеть
    ETHERNET = 4, _('Ethernet')  # стационарные сети передачи данных
    TMC = 5, _('TMC')
    MOBILE = 6, _('Mobile')
    WIFI = 7, 'WIFI'
    WiMAX = 8, 'WiMAX'
    paging = 9, _('Personal radio call')
    VOIP = 10, 'VOIP SIP'  # сеть передачи голосовой информации посредством сети передачи данных


class CustomerTypeChoices(models.IntegerChoices):
    INDIVIDUAL_ENTITY = 0, _('Individual entity')   # Физическое лицо
    LEGAL_ENTITY = 1, _('Legal entity')             # Юридическое лицо


class CustomerDocumentTypeChoices(models.TextChoices):
    PASSPORT_RF = _('Passport RF')
    PASSPORT_USSR = _('Passport USSR')
    PASSPORT_OTHER_COUNTRY = _('Passport other country')
    MILITARY_TICKET = _('Military ticket')


class Choice4BooleanField(models.TextChoices):
    YES = '1'
    NO = '0'
