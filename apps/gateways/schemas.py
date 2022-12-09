from typing import Optional
from ipaddress import IPv4Address
from datetime import datetime

from django.utils.translation import gettext as _
from gateways.gw_facade import GatewayTypesEnum
from gateways.models import GatewayClassChoices
from pydantic import Field, BaseModel
from djing2.lib.mixins import SitesBaseSchema


class GatewayBaseSchema(SitesBaseSchema):
    title: str = Field(max_length=127, title=_("Title"))
    ip_address: IPv4Address
    ip_port: int = Field(gt=0, lt=65535, title=_("Port"))
    auth_login: str = Field(max_length=64, title=_("Auth login"))
    gw_type: GatewayTypesEnum = Field(GatewayTypesEnum.MIKROTIK, title=_("Type"))
    gw_class: GatewayClassChoices = Field(GatewayClassChoices.UNKNOWN, title=_("Gateway class"))
    is_default: bool = Field(False, title=_("Is default"))
    enabled: bool = Field(True, title=_("Enabled"))
    place: Optional[str] = Field(None, max_length=256, title=_("Device place address"))


class GatewayWriteOnlySchema(GatewayBaseSchema):
    auth_passw: str = Field(title=_("Auth password"), max_length=127)


class GatewayModelSchema(GatewayBaseSchema):
    title: Optional[str] = Field(None, max_length=127, title=_("Title"))
    ip_address: Optional[IPv4Address] = None
    ip_port: int = Field(0, gt=0, lt=65535, title=_("Port"))
    auth_login: Optional[str] = Field(None, max_length=64, title=_("Auth login"))
    create_time: Optional[datetime] = Field(None, title=_("Create time"))
    gw_type_str: str = ''
    customer_count: int = 0
    customer_count_active: int = 0
    customer_count_w_service: int = 0


class GwClassChoice(BaseModel):
    v: int
    t: str
