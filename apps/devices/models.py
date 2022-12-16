from datetime import datetime
from typing import Optional

from netfields import MACAddressField
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _

from devices.schemas import DeviceOnuConfigTemplateSchema
from djing2.lib import MyChoicesAdapter
from djing2.lib.mixins import RemoveFilterQuerySetMixin
from djing2.models import BaseAbstractModel
from devices.device_config.device_type_collection import DEVICE_TYPE_UNKNOWN, DEVICE_TYPES
from devices.device_config.base import (
    Vlans,
    Macs,
    DeviceConfigurationError,
    OptionalScriptCallResult,
)
from devices.device_config.base_device_strategy import BaseDeviceStrategyContext
from devices.device_config.pon.pon_device_strategy import PonOLTDeviceStrategyContext, PonONUDeviceStrategyContext
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategyContext
from groupapp.models import Group
from networks.models import VlanIf
from addresses.interfaces import IAddressContaining
from addresses.models import AddressModel, AddressModelTypes


class DeviceModelQuerySet(RemoveFilterQuerySetMixin, models.QuerySet):
    def filter_devices_by_addr(self, addr_id: int):
        # Получить все устройства для населённого пункта.
        # Get all devices in specified location by their address_id.

        # get locality from addr
        addr_locality = AddressModel.objects.get_address_by_type(
            addr_id=addr_id,
            addr_type=AddressModelTypes.LOCALITY
        ).first()

        if addr_locality is None:
            addr_query = AddressModel.objects.get_address_by_type(
                addr_id=addr_id,
                addr_type=AddressModelTypes.LOCALITY
            )
        else:
            addr_query = AddressModel.objects.get_address_by_type(
                addr_id=addr_locality.pk,
                addr_type=AddressModelTypes.LOCALITY
            )
        if not addr_query.exists():
            return self
        return self.remove_filter('address_id').filter(
            address__in=AddressModel.objects.get_address_recursive_ids(addr_query.first().pk)
        )


class DeviceStatusEnum(models.IntegerChoices):
    NETWORK_STATE_UNDEFINED = 0, _("Undefined")
    NETWORK_STATE_UP = 1, _('Up')
    NETWORK_STATE_UNREACHABLE = 2, _('Unreachable')
    NETWORK_STATE_DOWN = 3, _('Down')


class Device(IAddressContaining, BaseAbstractModel):
    ip_address = models.GenericIPAddressField(verbose_name=_("Ip address"), null=True, blank=True, default=None)
    mac_addr = MACAddressField(verbose_name=_("Mac address"), unique=True)
    comment = models.CharField(_("Comment"), max_length=256)
    dev_type = models.PositiveSmallIntegerField(
        _("Device type"), default=DEVICE_TYPE_UNKNOWN, choices=MyChoicesAdapter(DEVICE_TYPES)
    )
    man_passw = models.CharField(_("SNMP password"), max_length=16, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Device group"))
    parent_dev = models.ForeignKey(
        "self", verbose_name=_("Parent device"), blank=True, null=True, on_delete=models.SET_NULL
    )
    snmp_extra = models.CharField(_("SNMP extra info"), max_length=256, null=True, blank=True)
    extra_data = models.JSONField(
        verbose_name=_("Extra data"),
        help_text=_("Extra data in JSON format. You may use it for your custom data"),
        blank=True,
        null=True,
    )
    vlans = models.ManyToManyField(VlanIf, verbose_name=_("Available vlans"), blank=True)

    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=DeviceStatusEnum.choices,
        default=DeviceStatusEnum.NETWORK_STATE_UNDEFINED
    )

    is_noticeable = models.BooleanField(_("Send notify when monitoring state changed"), default=False)

    code = models.CharField(
        _("Code"), max_length=64, blank=True,
        null=True, default=None
    )

    create_time = models.DateTimeField(
        _("Create time"),
        default=datetime.now,
    )

    address = models.ForeignKey(
        AddressModel, on_delete=models.SET_NULL, blank=True, null=True, default=None
    )

    sites = models.ManyToManyField(Site, blank=True)

    objects = DeviceModelQuerySet.as_manager()

    class Meta:
        db_table = "device"
        verbose_name = _("Device")
        verbose_name_plural = _("Devices")
        permissions = [
            ("can_remove_from_olt", _("Can remove from OLT")),
            ("can_fix_onu", _("Can fix onu")),
            ("can_apply_onu_config", _("Can apply onu config")),
        ]

    def get_address(self):
        return self.address

    def get_pon_olt_device_manager(self) -> PonOLTDeviceStrategyContext:
        return PonOLTDeviceStrategyContext(model_instance=self)

    def get_pon_onu_device_manager(self) -> PonONUDeviceStrategyContext:
        return PonONUDeviceStrategyContext(model_instance=self)

    def get_switch_device_manager(self) -> SwitchDeviceStrategyContext:
        return SwitchDeviceStrategyContext(model_instance=self)

    def get_general_device_manager(self) -> BaseDeviceStrategyContext:
        return BaseDeviceStrategyContext(model_instance=self)

    def __str__(self):
        return "{} {}".format(self.ip_address or "", self.comment)

    def remove_from_olt(self, extra_data=None, **kwargs) -> bool:
        if extra_data is None:
            pdev = self.parent_dev
            if not pdev:
                raise DeviceConfigurationError(_("You should config parent OLT device for ONU"))
            if not pdev.extra_data:
                raise DeviceConfigurationError(_("You have not info in extra_data field, please fill it in JSON"))
            extra_data = dict(pdev.extra_data)
        mng = self.get_pon_onu_device_manager()
        r = mng.remove_from_olt(extra_data=extra_data, **kwargs)
        if r:
            Device.objects.filter(pk=self.pk).update(snmp_extra=None)
        return r

    def fix_onu(self) -> tuple[Optional[int], Optional[str]]:
        mng = self.get_pon_onu_device_manager()
        onu_sn, err_text = mng.find_onu()
        if onu_sn is not None:
            Device.objects.filter(pk=self.pk).update(snmp_extra=str(onu_sn))
            return True, _("Fixed")
        return False, err_text

    def get_if_name(self):
        mng = self.get_pon_onu_device_manager()
        return mng.get_fiber_str()

    def get_config_types(self):
        mng = self.get_pon_onu_device_manager()
        return mng.get_config_types()

    def apply_onu_config(self, config: DeviceOnuConfigTemplateSchema) -> OptionalScriptCallResult:
        self.code = config.configTypeCode
        self.save(update_fields=["code"])
        all_device_types = self.get_config_types()
        self_device_type_code = str(self.code)
        dtypes = (dtype for dtype in all_device_types if dtype.short_code == self_device_type_code)
        dtype_for_run = next(dtypes, None)
        if dtype_for_run is not None:
            device_manager = dtype_for_run(title=dtype_for_run.title, code=dtype_for_run.short_code)
            return device_manager.entry_point(config=config, device=self)

    #############################
    #  Remote access(i.e. snmp)
    #############################

    def dev_get_all_vlan_list(self) -> Vlans:
        mng = self.get_general_device_manager()
        return mng.read_all_vlan_info()

    def read_onu_vlan_info(self) -> Vlans:
        mng = self.get_pon_onu_device_manager()
        return mng.read_onu_vlan_info()

    def default_vlan_info(self) -> Vlans:
        mng = self.get_pon_onu_device_manager()
        return mng.default_vlan_info()

    @property
    def is_onu_registered(self) -> bool:
        return self.snmp_extra is not None

    def dev_read_mac_address_vlan(self, vid: int) -> Macs:
        mng = self.get_switch_device_manager()
        return mng.read_mac_address_vlan(vid=vid)

    ##############################
    # Switch telnet methods
    ##############################

    # @_telnet_methods_wrapper
    # def telnet_switch_attach_vlan_to_port(self, tln: BaseSwitchInterface, vid: int,
    #                                       port: int, tag: bool = True) -> bool:
    #     return tln.attach_vlan_to_port(vid=vid, port=port, tag=tag)

    def dev_switch_get_mac_address_port(self, device_port_num: int) -> Macs:
        mng = self.get_switch_device_manager()
        return mng.read_mac_address_port(port_num=device_port_num)

    @property
    def dev_type_str(self) -> str:
        return getattr(self, 'get_dev_type_display', lambda: '-')()

    @property
    def iface_name(self) -> str:
        return self.get_if_name()

    @property
    def parent_dev_name(self):
        if self.parent_dev:
            return str(self.parent_dev)

    @property
    def parent_dev_group(self):
        if self.parent_dev.group:
            return self.parent_dev.group_id

    @property
    def address_title(self):
        return self.get_address()

    @property
    def attached_users(self):
        return self.customer_set.all()


class PortVlanMemberMode(models.IntegerChoices):
    NOT_CHOSEN = 0, _("Not chosen")
    DEFAULT = 1, _("Default")
    UNTAG = 2, _("Untagged")
    TAGGED = 3, _("Tagged")
    HYBRID = 4, _("Hybrid")


class PortVlanMemberModel(BaseAbstractModel):
    vlanif = models.ForeignKey(VlanIf, on_delete=models.CASCADE)
    port = models.ForeignKey("Port", on_delete=models.CASCADE)
    mode = models.PositiveSmallIntegerField(
        _("Operating mode"), default=PortVlanMemberMode.NOT_CHOSEN, choices=PortVlanMemberMode.choices
    )


class PortOperatingMode(models.IntegerChoices):
    NOT_CHOSEN = 0, _("Not chosen")
    ACCESS = 1, _("Access")
    TRUNK = 2, _("Trunk")
    HYBRID = 3, _("Hybrid")
    GENERAL = 4, _("General")


class Port(BaseAbstractModel):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, verbose_name=_("Device"))
    num = models.PositiveSmallIntegerField(_("Number"), default=0)
    descr = models.CharField(_("Description"), max_length=60, null=True, blank=True)
    operating_mode = models.PositiveSmallIntegerField(
        _("Operating mode"), default=PortOperatingMode.NOT_CHOSEN, choices=PortOperatingMode.choices
    )
    vlans = models.ManyToManyField(
        VlanIf, through=PortVlanMemberModel, verbose_name=_("VLan list"), through_fields=("port", "vlanif")
    )
    create_time = models.DateTimeField(
        _("Create time"),
        default=datetime.now,
    )

    # config_type = models.PositiveSmallIntegerField

    def __str__(self):
        return "%d: %s" % (self.num, self.descr)

    def get_port_vlan_list(self) -> Vlans:
        dev: Device = self.device
        mng = dev.get_switch_device_manager()
        yield from mng.read_port_vlan_info(port=int(self.num))

    class Meta:
        db_table = "device_port"
        unique_together = ("device", "num")
        permissions = [
            ("can_toggle_ports", _("Can toggle ports")),
        ]
        verbose_name = _("Port")
        verbose_name_plural = _("Ports")
