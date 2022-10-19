from fastapi import APIRouter
from addresses.views import router as addrs_router
from sorm_export.views import router as sorm_r
from customer_comments.views import router as custocomm_rt
from customer_contract.views import router as custocontr_rt
from customers_duplicates.views import router as dup_rt
from radiusapp.views import router as radius_rt
from customers.views import router as customers_router


router = APIRouter(
    prefix='/api',
)

router.include_router(addrs_router)
router.include_router(sorm_r)
router.include_router(custocomm_rt)
router.include_router(custocontr_rt)
router.include_router(dup_rt)
router.include_router(radius_rt)
router.include_router(customers_router)
