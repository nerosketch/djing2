from fastapi import APIRouter
from .customer_service import router as csr
from .shot import router as shot_rt
from .periodic import router as per_rt

router = APIRouter(
    prefix='/services',
    tags=['Services']
)

router.include_router(csr)
router.include_router(shot_rt)
router.include_router(per_rt)
