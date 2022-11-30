from typing import Optional

from djing2.lib.fastapi.types import OrmConf
from djing2.lib.mixins import SitesBaseSchema
from pydantic import BaseModel, Field


class GroupBaseSchema(BaseModel):
    title: str = Field(max_length=127)


class GroupsModelSchema(SitesBaseSchema, GroupBaseSchema):
    id: Optional[int] = None

    Config = OrmConf
