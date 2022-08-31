from typing import Optional

from django.utils.translation import gettext
from pydantic import BaseModel, root_validator, Field
from addresses.models import AddressModelTypes


class AddressBaseSchema(BaseModel):
    parent_addr_id: Optional[int] = None
    title: str
    address_type: AddressModelTypes
    fias_address_level: int = Field(0, gt=0)
    fias_address_type: int = Field(0, gt=0)

    @root_validator
    def validate_title(cls, values: dict):
        address_type = values.get('address_type')
        if not address_type:
            raise ValueError("address_type can not be empty")
        # Квартиры, дома, номера офисов могут быть только числовыми
        addr_num_types = (
            AddressModelTypes.HOUSE.value,
            AddressModelTypes.OFFICE_NUM.value,
        )
        if address_type in addr_num_types:
            title = values.get('title')
            title = title.strip()
            try:
                int(title)
            except ValueError:
                raise ValueError(gettext("House and office can be only number"))
        return values


class AddressModelSchema(BaseModel):
    id: Optional[int]
    parent_addr_id: Optional[int] = None
    title: Optional[str]
    address_type: Optional[AddressModelTypes]
    fias_address_level: Optional[int] = Field(None, gt=0)
    fias_address_type: Optional[int] = Field(None, gt=0)
    parent_addr_title: Optional[str]
    fias_address_level_name: Optional[str]
    fias_address_type_name: Optional[str]
    children_count: Optional[int]

    class Config:
        orm_mode = True
