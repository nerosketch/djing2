from typing import Optional
from pydantic import BaseModel


class AccountSearchResponse(BaseModel):
    id: int
    fio: str
    username: str
    ips: list[str]
    telephone: Optional[str] = None
    gid: Optional[int] = None
    group_title: Optional[str] = None


class DeviceSearchResponse(BaseModel):
    id: int
    comment: str
    ip_address: Optional[str] = None
    mac_addr: Optional[str] = None
    dev_type_str: str
    gid: Optional[int] = None


class SearchResultModel(BaseModel):
    accounts: list[AccountSearchResponse]
    devices: list[DeviceSearchResponse]
