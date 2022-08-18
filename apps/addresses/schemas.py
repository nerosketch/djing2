from pydantic import BaseModel
from addresses.models import AddressModelTypes


class AddressBaseSchema(BaseModel):
    parent_addr: int
    address_type: AddressModelTypes
    fias_address_level: int
    fias_address_type: int
    title: str


class AddressModelSchema(AddressBaseSchema):
    id: int

