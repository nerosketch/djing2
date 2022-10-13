from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from djing2.lib.fastapi.types import OrmConf
from services.custom_logic import ServiceChoiceEnum


class ServiceModelBaseSchema(BaseModel):
    title: str
    descr: Optional[str] = None
    speed_in: float = Field(ge=0.1)
    speed_out: float = Field(ge=0.1)
    speed_burst: float = 1.0
    cost: float = Field(ge=0.0)
    calc_type: ServiceChoiceEnum
    is_admin: bool = False


class ServiceModelSchema(ServiceModelBaseSchema):
    id: int
    create_time: Optional[datetime] = None
    usercount: int
    planned_deadline: str
    calc_type_name: Optional[str] = None

    Config = OrmConf
