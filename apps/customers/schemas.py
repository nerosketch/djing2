from typing import Optional, List

from profiles.schemas import BaseAccountModelSchema, BaseAccountSchema


class CustomerSchema(BaseAccountSchema):
    balance: float
    current_service_id: Optional[int] = None
    group_id: Optional[int] = None
    address_id: Optional[int] = None
    description: Optional[str] = None
    device_id: Optional[int] = None
    dev_port: Optional[int] = None
    is_dynamic_ip: bool = False
    gateway_id: Optional[int] = None
    auto_renewal_service: bool = False
    last_connected_service_id: Optional[int] = None


class CustomerModelSchema(BaseAccountModelSchema):
    id: int
    group_title: Optional[str]
    address_title: str
    device_comment: Optional[str]
    last_connected_service_title: Optional[str]
    current_service_title: Optional[str]
    service_id: Optional[int]
    raw_password: Optional[str]
    lease_count: Optional[int] = None
    marker_icons: List[str] = ()

    class Config:
        orm_mode = True
