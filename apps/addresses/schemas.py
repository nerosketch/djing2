from typing import Optional

from django.utils.translation import gettext
from pydantic import BaseModel, root_validator, Field
from addresses.models import AddressModelTypes


class AddressBaseSchema(BaseModel):
    parent_addr: Optional[int] = None
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


class AddressModelSchema(AddressBaseSchema):
    id: int

    @property
    def parent_addr_title(self):
        return getattr(self, 'parent_addr').title
        # return self.parent_addr.title

    @property
    def fias_address_level_name(self):
        return self.get_fias_address_level_display()

    @property
    def fias_address_type_name(self):
        return 'fias_address_type_name'

    @property
    def children_count(self):
        return 12

    class Config:
        orm_mode = True
