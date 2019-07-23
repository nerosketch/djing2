from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _
from netfields import MACAddressField

from devices import dev_types
from devices.base_intr import DevBase
from djing2.lib import MyChoicesAdapter
from groupapp.models import Group


class Device(models.Model):
    _cached_manager = None

    ip_address = models.GenericIPAddressField(
        verbose_name=_('Ip address'),
        null=True, blank=True
    )
    mac_addr = MACAddressField(
        verbose_name=_('Mac address'),
        unique=True
    )
    comment = models.CharField(_('Comment'), max_length=256)
    DEVICE_TYPES = (
        (1, dev_types.DLinkDevice),
        (2, dev_types.OLTDevice),
        (3, dev_types.OnuDevice),
        (4, dev_types.EltexSwitch),
        (5, dev_types.Olt_ZTE_C320),
        (6, dev_types.ZteOnuDevice),
        (7, dev_types.ZteF601),
        (8, dev_types.HuaweiSwitch)
    )
    dev_type = models.PositiveSmallIntegerField(
        _('Device type'), default=1,
        choices=MyChoicesAdapter(DEVICE_TYPES)
    )
    man_passw = models.CharField(
        _('SNMP password'), max_length=16,
        null=True, blank=True
    )
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, null=True,
        blank=True, verbose_name=_('Device group')
    )
    parent_dev = models.ForeignKey(
        'self', verbose_name=_('Parent device'),
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    snmp_extra = models.CharField(
        _('SNMP extra info'), max_length=256,
        null=True, blank=True
    )
    extra_data = JSONField(
        verbose_name=_('Extra data'),
        help_text=_('Extra data in JSON format. You may use it for your custom data'),
        blank=True, null=True
    )

    NETWORK_STATES = (
        (0, _('Undefined')),
        (1, _('Up')),
        (2, _('Unreachable')),
        (3, _('Down'))
    )
    status = models.PositiveSmallIntegerField(_('Status'), choices=NETWORK_STATES, default=0)

    is_noticeable = models.BooleanField(_('Send notify when monitoring state changed'), default=False)

    class Meta:
        db_table = 'device'
        verbose_name = _('Device')
        verbose_name_plural = _('Devices')
        ordering = ('id',)

    def get_manager_klass(self):
        try:
            return next(klass for code, klass in self.DEVICE_TYPES if code == int(self.dev_type))
        except StopIteration:
            raise TypeError('one of types is not subclass of DevBase. '
                            'Or implementation of that device type is not found')

    def get_manager_object(self) -> DevBase:
        man_klass = self.get_manager_klass()
        if self._cached_manager is None:
            self._cached_manager = man_klass(self)
        return self._cached_manager

    # Can attach device to customer in customer page
    def has_attachable_to_customer(self) -> bool:
        mngr = self.get_manager_klass()
        return mngr.has_attachable_to_customer

    def __str__(self):
        return "%s: (%s) %s %s" % (
            self.comment, self.get_dev_type_display(),
            self.ip_address or '', self.mac_addr or ''
        )

    def generate_config_template(self):
        mng = self.get_manager_object()
        return mng.monitoring_template()

    def register_device(self):
        mng = self.get_manager_object()
        if not self.extra_data:
            if self.parent_dev and self.parent_dev.extra_data:
                return mng.register_device(self.parent_dev.extra_data)
        return mng.register_device(dict(self.extra_data))


class Port(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        verbose_name=_('Device')
    )
    num = models.PositiveSmallIntegerField(_('Number'), default=0)
    descr = models.CharField(_('Description'), max_length=60, null=True, blank=True)

    def __str__(self):
        return "%d: %s" % (self.num, self.descr)

    def scan_additional(self):
        if not self.device:
            return
        mng = self.device.get_manager_object()
        return mng.get_port(snmp_num=self.num).to_dict()

    class Meta:
        db_table = 'device_port'
        unique_together = ('device', 'num')
        permissions = (
            ('can_toggle_ports', _('Can toggle ports')),
        )
        verbose_name = _('Port')
        verbose_name_plural = _('Ports')
        ordering = ('num',)
