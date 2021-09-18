from django.utils.translation import gettext as _
from django.db.models import JSONField
from django.db import models, connection
from addresses.models import LocalityModel
from sorm_export.fias_socrbase import AddressFIASLevelChoices, AddressFIASInfo

date_format = '%d.%m.%Y'
datetime_format = '%d.%m.%YT%H:%M:%S'


class ExportFailedStatus(Exception):
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


"""
class FtpCredentialsModel(models.Model):
    host = models.CharField(
        verbose_name=_('Hostname'),
        max_length=128
    )
    login = models.CharField(
        verbose_name=_('Login'),
        max_length=64
    )
    password = EncryptedCharField(max_length=64)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.host

    class Meta:
        db_table = 'sorm_export_ftp_credentials'
"""


ao_type_choices = ((num, '%s' % name[0]) for lev, inf in AddressFIASInfo.items() for num, name in inf.items())


class FiasRecursiveAddressModelManager(models.Manager):
    @staticmethod
    def get_streets_as_addr_objects():
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_streets_as_addr_objects;")
            res = cur.fetchone()
            while res is not None:
                # res: street_id, parent_ao_id, parent_ao_type, street_name
                yield res
                res = cur.fetchone()


class FiasRecursiveAddressModel(models.Model):
    parent_ao = models.ForeignKey(
        'self', verbose_name=_('Parent AO'),
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True,
        default=None
    )
    title = models.CharField(_('Title'), max_length=128)
    ao_level = models.IntegerField(_('AO Level'), choices=AddressFIASLevelChoices)
    ao_type = models.IntegerField(
        _('AO Type'),
        choices=ao_type_choices
    )
    localities = models.ManyToManyField(LocalityModel, blank=True)

    objects = FiasRecursiveAddressModelManager()

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'sorm_address'
