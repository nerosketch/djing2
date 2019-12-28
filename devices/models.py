from typing import Optional, Tuple, ClassVar

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _
from netfields import MACAddressField

from devices.switch_config import DEVICE_TYPES
from devices.switch_config.base import DevBase, DeviceConfigurationError
from djing2.lib import MyChoicesAdapter, safe_int
from groupapp.models import Group
from networks.models import VlanIf


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
    dev_type = models.PositiveSmallIntegerField(
        _('Device type'), default=0,
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

    def get_manager_klass(self) -> ClassVar[DevBase]:
        try:
            return next(klass for code, klass in DEVICE_TYPES if code == safe_int(self.dev_type))
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

    def remove_from_olt(self):
        pdev = self.parent_dev
        if not pdev:
            raise DeviceConfigurationError(_('You should config parent OLT device for ONU'))
        if not pdev.extra_data:
            raise DeviceConfigurationError(_('You have not info in extra_data '
                                             'field, please fill it in JSON'))
        mng = self.get_manager_object()
        r = mng.remove_from_olt(pdev.extra_data)
        if r:
            self.snmp_extra = None
            self.save(update_fields=['snmp_extra'])
        return r

    def onu_find_sn_by_mac(self) -> Tuple[Optional[int], Optional[str]]:
        parent = self.parent_dev
        if parent is not None:
            manager = parent.get_manager_object()
            mac = self.mac_addr
            ports = manager.get_list_keyval('.1.3.6.1.4.1.3320.101.10.1.1.3')
            for srcmac, snmpnum in ports:
                # convert bytes mac address to str presentation mac address
                real_mac = ':'.join('%x' % ord(i) for i in srcmac)
                if mac == real_mac:
                    return safe_int(snmpnum), None
            return None, _('Onu with mac "%(onu_mac)s" not found on OLT') % {
                'onu_mac': mac
            }
        return None, _('Parent device not found')

    def fix_onu(self):
        onu_sn, err_text = self.onu_find_sn_by_mac()
        if onu_sn is not None:
            self.snmp_extra = str(onu_sn)
            self.save(update_fields=('snmp_extra',))
            return True, _('Fixed')
        return False, err_text


class PortVlanMemberModel(models.Model):
    vlanif = models.ForeignKey(VlanIf, on_delete=models.CASCADE)
    port = models.ForeignKey('Port', on_delete=models.CASCADE)
    VLAN_OPERATING_MODES = (
        (0, _('Not chosen')),
        (1, _('Default')),
        (2, _('Untagged')),
        (3, _('Tagged')),
        (4, _('Hybrid'))
    )
    mode = models.PositiveSmallIntegerField(
        _('Operating mode'), default=0,
        choices=VLAN_OPERATING_MODES
    )


class Port(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE,
        verbose_name=_('Device')
    )
    num = models.PositiveSmallIntegerField(_('Number'), default=0)
    descr = models.CharField(_('Description'), max_length=60, null=True, blank=True)
    PORT_OPERATING_MODES = (
        (0, _('Not chosen')),
        (1, _('Access')),
        (2, _('Trunk')),
        (3, _('Hybrid')),
        (4, _('General'))
    )
    operating_mode = models.PositiveSmallIntegerField(
        _('Operating mode'), default=0,
        choices=PORT_OPERATING_MODES
    )
    vlans = models.ManyToManyField(
        VlanIf, through=PortVlanMemberModel,
        verbose_name=_('VLan list'),
        through_fields=('port', 'vlanif')
    )
    # config_type = models.PositiveSmallIntegerField

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
