from typing import Optional, Tuple

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _
from netfields import MACAddressField

from devices.switch_config import (
    DEVICE_TYPES, Vlans, Macs,
    BaseSwitchInterface, BasePONInterface, BasePON_ONU_Interface,
    BaseDeviceInterface,
    DeviceConfigurationError,
    # port_templates_modules,
    DeviceImplementationError, Vlan, DEVICE_TYPE_UNKNOWN)

from djing2.lib import MyChoicesAdapter, safe_int, macbin2str
from groupapp.models import Group
from networks.models import VlanIf


# def _telnet_methods_wrapper(fn):
#     def _wrapper(self, *args, **kwargs):
#         if not self.extra_data:
#             raise DeviceConfigurationError(_('You have not info in extra_data '
#                                              'field, please fill it in JSON'))
#         extra_data = dict(self.extra_data)
#         extra_data_telnet = extra_data.get('telnet')
#         if not extra_data_telnet:
#             raise DeviceConfigurationError('telnet credentials required in "extra_data"')
#         tlogin = extra_data_telnet.get('login')
#         tpassw = extra_data_telnet.get('password')
#         tprompt = extra_data_telnet.get('prompt')
#         if not all((tlogin, tpassw, extra_data_telnet, tprompt)):
#             raise DeviceConfigurationError('telnet credentials required in "extra_data"')
#         mng = self.get_manager_klass()

#         with mng(host=str(self.ip_address), prompt=tprompt.encode()) as tln:
#             if not tln.login(login=tlogin, password=tpassw):
#                 raise DeviceConsoleError(_('Login failed'))
#             try:
#                 return fn(self, tln, *args, **kwargs)
#             except (ValueError, RuntimeError) as e:
#                 raise DeviceConsoleError(e)
#     return _wrapper


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
        _('Device type'), default=DEVICE_TYPE_UNKNOWN,
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
    vlans = models.ManyToManyField(VlanIf, verbose_name=_('Available vlans'), blank=True)

    NETWORK_STATE_UNDEFINED = 0
    NETWORK_STATE_UP = 1
    NETWORK_STATE_UNREACHABLE = 2
    NETWORK_STATE_DOWN = 3
    NETWORK_STATES = (
        (NETWORK_STATE_UNDEFINED, _('Undefined')),
        (NETWORK_STATE_UP, _('Up')),
        (NETWORK_STATE_UNREACHABLE, _('Unreachable')),
        (NETWORK_STATE_DOWN, _('Down'))
    )
    status = models.PositiveSmallIntegerField(_('Status'), choices=NETWORK_STATES, default=NETWORK_STATE_UNDEFINED)

    is_noticeable = models.BooleanField(_('Send notify when monitoring state changed'), default=False)

    class Meta:
        db_table = 'device'
        verbose_name = _('Device')
        verbose_name_plural = _('Devices')
        ordering = ('id',)

    def get_manager_klass(self) -> BaseDeviceInterface:
        try:
            return next(klass for code, klass in DEVICE_TYPES if code == safe_int(self.dev_type))
        except StopIteration:
            raise TypeError('one of types is not subclass of BaseDeviceInterface. '
                            'Or implementation of that device type is not found')

    def get_manager_object(self) -> BaseDeviceInterface:
        man_klass = self.get_manager_klass()
        if self._cached_manager is None:
            self._cached_manager = man_klass(
                dev_instance=self
            )
        return self._cached_manager

    def get_manager_object_switch(self) -> BaseSwitchInterface:
        man_klass = self.get_manager_klass()
        if self._cached_manager is None:
            self._cached_manager = man_klass(
                dev_instance=self,
                host=str(self.ip_address),
                snmp_community=str(self.man_passw)
            )
        return self._cached_manager

    def get_manager_object_olt(self) -> BasePONInterface:
        man_klass = self.get_manager_klass()
        if self._cached_manager is None:
            self._cached_manager = man_klass(
                dev_instance=self
            )
        return self._cached_manager

    def get_manager_object_onu(self) -> BasePON_ONU_Interface:
        man_klass = self.get_manager_klass()
        if self._cached_manager is None:
            self._cached_manager = man_klass(
                dev_instance=self
            )
        return self._cached_manager

    # Can attach device to customer in customer page
    def has_attachable_to_customer(self) -> bool:
        mngr = self.get_manager_klass()
        return mngr.has_attachable_to_customer

    def __str__(self):
        return "%s: (%s) %s. %s" % (
            self.comment, self.get_dev_type_display(),
            self.ip_address or '', self.mac_addr or ''
        )

    def generate_config_template(self):
        mng = self.get_manager_object()
        return mng.monitoring_template()

    def register_device(self):
        mng = self.get_manager_object_olt()
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
        mng = self.get_manager_object_olt()
        r = mng.remove_from_olt(dict(pdev.extra_data))
        if r:
            self.snmp_extra = None
            self.save(update_fields=['snmp_extra'])
        return r

    def onu_find_sn_by_mac(self) -> Tuple[Optional[int], Optional[str]]:
        parent = self.parent_dev
        if parent is not None:
            manager = parent.get_manager_object_olt()
            mac = self.mac_addr
            ports = manager.get_list_keyval('.1.3.6.1.4.1.3320.101.10.1.1.3')
            for srcmac, snmpnum in ports:
                # convert bytes mac address to str presentation mac address
                real_mac = macbin2str(srcmac)
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

    #############################
    #  Remote access(i.e. snmp)
    #############################

    def dev_get_all_vlan_list(self) -> Vlans:
        mng = self.get_manager_object_switch()
        return mng.read_all_vlan_info()

    # @_telnet_methods_wrapper
    # def dev_create_vlans(self, tln: BaseDeviceInterface, vids: Vlans) -> None:
    #     if not tln.create_vlans(vids):
    #         raise DeviceConsoleError(_('Failed while create vlans'))

    # @_telnet_methods_wrapper
    # def dev_delete_vlan(self, tln: BaseDeviceInterface, vids: Vlans) -> None:
    #     if not tln.delete_vlans(vlan_list=vids):
    #         raise DeviceConsoleError(_('Failed while removing vlan'))

    def dev_read_mac_address_vlan(self, vid: int) -> Macs:
        mng = self.get_manager_object_switch()
        return mng.read_mac_address_vlan(vid=vid)

    ##############################
    # Switch telnet methods
    ##############################

    # @_telnet_methods_wrapper
    # def telnet_switch_attach_vlan_to_port(self, tln: BaseSwitchInterface, vid: int,
    #                                       port: int, tag: bool = True) -> bool:
    #     return tln.attach_vlan_to_port(vid=vid, port=port, tag=tag)

    # @_telnet_methods_wrapper
    # def telnet_switch_detach_vlan_from_port(self, tln: BaseSwitchInterface, vid: int, port: int) -> bool:
    #     return tln.detach_vlan_from_port(vid=vid, port=port)

    def dev_switch_get_mac_address_port(self, device_port_num: int) -> Macs:
        mng = self.get_manager_object_switch()
        return mng.read_mac_address_port(port_num=device_port_num)

    ##############################
    # PON telnet methods
    ##############################

    # @_telnet_methods_wrapper
    # def telnet_pon_attach_vlans_to_uplink(self, tln: BasePONInterface, vids: Iterable[int], *args, **kwargs) -> None:
    #     return tln.attach_vlans_to_uplink(vids=vids, *args, **kwargs)


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

    def get_port_vlan_list(self) -> Vlans:
        mng = self.device.get_manager_object_switch()
        yield from mng.read_port_vlan_info(port=int(self.num))

    def apply_vlan_config(self, serializer):
        device = self.device
        if not device:
            raise DeviceImplementationError('device could not found')
        port_num = serializer.data.get('port_num')
        if not port_num:
            raise DeviceImplementationError('port_num field required')

        mng = device.get_manager_object_switch()

        vlans_data = serializer.data.get('vlans')
        if not vlans_data:
            raise DeviceImplementationError('vlans field required')

        vlans_gen = (Vlan(**v) for v in vlans_data)

        mng.attach_vlans_to_port(vlan_list=vlans_gen, port_num=port_num)

    class Meta:
        db_table = 'device_port'
        unique_together = ('device', 'num')
        permissions = (
            ('can_toggle_ports', _('Can toggle ports')),
        )
        verbose_name = _('Port')
        verbose_name_plural = _('Ports')
        ordering = ('num',)
