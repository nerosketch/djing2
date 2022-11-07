from fastapi import APIRouter
from .customer_service import router as csr

router = APIRouter(
    prefix='/services',
    tags=['Services']
)

router.include_router(csr)
