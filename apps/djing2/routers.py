from fastapi import APIRouter, Depends
from djing2.lib.fastapi.auth import token_auth_dep
from addresses.views import router as addrs_router
from sorm_export.views import router as sorm_r
from customer_comments.views import router as custocomm_rt
from customer_contract.views import router as custocontr_rt
from customers_duplicates.views import router as dup_rt
from customers_legal.views import router as legal_rt


router = APIRouter(
    prefix='/api',
    dependencies=[Depends(token_auth_dep)]
)

router.include_router(addrs_router)
router.include_router(sorm_r)
router.include_router(custocomm_rt)
router.include_router(custocontr_rt)
router.include_router(legal_rt)
router.include_router(dup_rt)
