from fastapi import APIRouter
from .customer_service import router as csr
from .shot import router as shot_rt
from .periodic import router as per_rt
from .service_queue import router as queue_rt
from .admin_side import router as adm_rt

router = APIRouter(
    prefix='/services',
    tags=['Services']
)

router.include_router(csr)
router.include_router(shot_rt)
router.include_router(per_rt)
router.include_router(queue_rt)
router.include_router(adm_rt)
