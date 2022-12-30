from datetime import datetime
from typing import Union, Optional
from ipaddress import IPv4Address, IPv6Address
from django.db.models import QuerySet
from django.utils.translation import gettext as _
from djing2.lib.mixins import SitesBaseSchema
from netaddr import EUI

from pydantic import BaseModel, Field, validator

from djing2.lib.fastapi.types import OrmConf

from .device_config.device_type_collection import DeviceTypeEnum
from .models import DeviceStatusEnum, PortVlanMemberMode


class DeviceWithoutGroupBaseSchema(BaseModel):
    ip_address: Optional[Union[IPv4Address, IPv6Address]] = Field(None, title=_("Ip address"))
    mac_addr: str
    comment: str = Field(max_length=256, title=_("Comment"))
    dev_type: DeviceTypeEnum = Field(default=DeviceTypeEnum.UnknownDevice, title=_("Device type"))
    man_passw: Optional[str] = Field(None, title=_("SNMP password"), max_length=16)
    parent_dev_id: Optional[int] = Field(None, title=_("Parent device"))
    snmp_extra: Optional[str] = Field(None, title=_("SNMP extra info"), max_length=256)
    is_noticeable: bool = Field(
        title=_("Send notify when monitoring state changed"),
        default=False
    )
    address_id: Optional[int] = None


class AttachedUserSchema(BaseModel):
    id: int
    full_name: str

    Config = OrmConf


class DeviceWithoutGroupModelSchema(DeviceWithoutGroupBaseSchema):
    id: Optional[int] = None
    mac_addr: Optional[str] = None
    comment: Optional[str] = None
    dev_type_str: str
    iface_name: str
    parent_dev_name: Optional[str] = None
    parent_dev_group: Optional[int] = None
    address_title: str
    attached_users: list[AttachedUserSchema] = []
    status: DeviceStatusEnum = Field(
        default=DeviceStatusEnum.NETWORK_STATE_UNDEFINED,
        title=_("Status")
    )

    @validator('mac_addr', pre=True)
    def validate_mac(cls, mac: str):
        if isinstance(mac, EUI):
            return str(mac)
        return mac

    @validator('attached_users', pre=True)
    def get_attached_users(cls, au):
        if isinstance(au, QuerySet):
            return [AttachedUserSchema.from_orm(i) for i in au]
        return au

    Config = OrmConf


class DeviceBaseSchema(DeviceWithoutGroupBaseSchema):
    group_id: Optional[int] = Field(None, title=_("Device group"))
    extra_data: Optional[dict] = Field(None, title=_("Extra data"))
    # vlans: list[int] = Field([], title=_("Available vlans"))
    code: Optional[str] = Field(None, title=_("Code"), max_length=64)


class DeviceUpdateSchema(DeviceBaseSchema, SitesBaseSchema):
    mac_addr: Optional[str] = None
    comment: Optional[str] = Field(None, max_length=256, title=_("Comment"))


class DeviceModelSchema(DeviceBaseSchema, DeviceWithoutGroupModelSchema):
    create_time: datetime = Field(title=_("Create time"))
    address_title: Optional[str] = None
    iface_name: Optional[str] = None


class DeviceModelSchemaWithSites(DeviceModelSchema, SitesBaseSchema):
    pass


class DevicePONModelSchema(DeviceModelSchema):
    pass


class PortBaseSchema(BaseModel):
    device_id: int
    num: int = 0
    descr: Optional[str] = Field(None, title=_("Description"), max_length=60)


class PortModelSchema(PortBaseSchema):
    id: Optional[int] = None
    user_count: Optional[int] = None

    Config = OrmConf


class PortVlanMemberBasSchema(BaseModel):
    vlanif_id: int
    port_id: int
    mode: PortVlanMemberMode = Field(PortVlanMemberMode.NOT_CHOSEN, title=_("Operating mode"))


class PortVlanMemberModelSchema(PortVlanMemberBasSchema):
    id: Optional[int] = None

    Config = OrmConf


class GroupsWithDevicesBaseSchema(BaseModel):
    title: str = Field(max_length=127)


class GroupsWithDevicesModelSchema(GroupsWithDevicesBaseSchema):
    id: Optional[int] = None
    device_count: Optional[int] = None

    Config = OrmConf


class FixOnuResponseSchema(BaseModel):
    text: str
    status: int = Field(
        description="1 if ok, else 2"
    )
    device: DevicePONModelSchema


class RemoveFromOLTResponseSchema(BaseModel):
    text: str
    status: int


class ZabbixNotificationData(BaseModel):
    dev_ip: Union[IPv4Address, IPv6Address]
    dev_status: DeviceStatusEnum
    message: str


class DeviceTypeName(BaseModel):
    nm: str
    v: int


class PonDetailsResult(BaseModel):
    info: list[tuple[str, str]]
    mac: Optional[str] = None
    signal: Optional[Union[float, str]] = None
    status: Optional[str] = None
    uptime: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    has_attachable_to_customer: bool = False
    is_use_device_port: bool = False
    disk_total: Optional[str] = None
    disk_free: Optional[str] = None
    fname: Optional[str] = None
    fver: Optional[str] = None
