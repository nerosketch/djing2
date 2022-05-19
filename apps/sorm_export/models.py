from django.utils.translation import gettext as _
from django.db.models import JSONField
from django.db import models
from djing2.lib import LogicError


date_format = '%d.%m.%Y'
datetime_format = '%d.%m.%YT%H:%M:%S'


class ExportFailedStatus(LogicError):
    pass


class ExportStampTypeEnum(models.IntegerChoices):
    UNKNOWN_CHOICE = 0
    CUSTOMER_ROOT = 1
    CUSTOMER_CONTRACT = 2
    CUSTOMER_ADDRESS = 3
    CUSTOMER_AP_ADDRESS = 4
    CUSTOMER_INDIVIDUAL = 5
    CUSTOMER_LEGAL = 6
    CUSTOMER_CONTACT = 7
    NETWORK_STATIC_IP = 8
    PAYMENT_UNKNOWN = 9
    SERVICE_NOMENCLATURE = 10
    SERVICE_CUSTOMER = 11
    SERVICE_CUSTOMER_MANUAL = 12
    DEVICE_SWITCH = 13
    IP_NUMBERING = 14
    GATEWAYS = 15


class ExportStampStatusEnum(models.IntegerChoices):
    NOT_EXPORTED = 0, _('Not exported')
    SUCCESSFUL = 1, _('Successful')
    FAILED = 2, _('Failed')


class ExportStampModel(models.Model):
    first_attempt_time = models.DateTimeField(_('Action time'), auto_now_add=True)
    last_attempt_time = models.DateTimeField(_('Last attempt time'), auto_now_add=True)
    attempts_count = models.IntegerField(_('Attempt count'), default=0)
    export_status = models.PositiveIntegerField(
        _('Export status'),
        choices=ExportStampStatusEnum.choices,
        default=ExportStampStatusEnum.NOT_EXPORTED
    )
    export_type = models.IntegerField(
        _('Export type'),
        choices=ExportStampTypeEnum.choices,
        default=ExportStampTypeEnum.UNKNOWN_CHOICE
    )
    data = JSONField(_('Export event data'))

    class Meta:
        db_table = 'sorm_export_stamp'


class CommunicationStandardChoices(models.IntegerChoices):
    NOT_CONCRETE = 0, 'unknown'
    GSM = 1, 'GSM'
    CDMA = 2, 'CDMA'
    PSTN = 3, 'PSTN'  # ТФоП сеть
    ETHERNET = 4, 'Ethernet'  # стационарные сети передачи данных
    TMC = 5, 'TMC'
    MOBILE = 6, 'mobile'
    WIFI = 7, 'WIFI'
    WiMAX = 8, 'WIMAX'
    paging = 9, 'paging'  # Personal radio call
    VOIP = 10, 'VOIP'  # сеть передачи голосовой информации посредством сети передачи данных


class CustomerTypeChoices(models.IntegerChoices):
    INDIVIDUAL_ENTITY = 0, _('Individual entity')   # Физическое лицо
    LEGAL_ENTITY = 1, _('Legal entity')             # Юридическое лицо


class CustomerDocumentTypeChoices(models.TextChoices):
    EMPTY = ''
    PASSPORT_RF = _('Passport RF')
    PASSPORT_USSR = _('Passport USSR')
    PASSPORT_OTHER_COUNTRY = _('Passport other country')
    MILITARY_TICKET = _('Military ticket')


class Choice4BooleanField(models.TextChoices):
    YES = '1'
    NO = '0'
