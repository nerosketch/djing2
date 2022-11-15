from pydantic import BaseModel


class CustomerServiceRequestSchema(BaseModel):
    customer_ip: str
    password: str
