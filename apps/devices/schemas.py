from datetime import datetime
from typing import Union, Optional
from ipaddress import IPv4Address, IPv6Address
from django.utils.translation import gettext as _

from pydantic import BaseModel, Field

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

    Config = OrmConf


class DeviceBaseSchema(DeviceWithoutGroupBaseSchema):
    group_id: Optional[int] = Field(None, title=_("Device group"))
    extra_data: Optional[dict] = Field(None, title=_("Extra data"))
    # vlans: list[int] = Field([], title=_("Available vlans"))
    code: Optional[str] = Field(None, title=_("Code"), max_length=64)


class DeviceModelSchema(DeviceBaseSchema, DeviceWithoutGroupModelSchema):
    create_time: datetime = Field(title=_("Create time"))


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


class DevOnuVlanSchema(BaseModel):
    vid: int = 1
    native: bool = False


class DevOnuVlanInfoTemplateSchema(BaseModel):
    port: int = 1
    vids: list[DevOnuVlanSchema] = []


class DeviceOnuConfigTemplateSchema(BaseModel):
    configTypeCode: str = Field(title=_("Config code"), max_length=64)
    vlanConfig: DevOnuVlanInfoTemplateSchema


class GroupsWithDevicesBaseSchema(BaseModel):
    title: str = Field(max_length=127)


class GroupsWithDevicesModelSchema(GroupsWithDevicesBaseSchema):
    id: Optional[int] = None
    device_count: Optional[int] = None

    Config = OrmConf
