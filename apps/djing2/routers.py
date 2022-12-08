from djing2.lib.fastapi.default_response_class import CompatibleJSONResponse
from fastapi import APIRouter
from addresses.views import router as addrs_router
from sorm_export.views import router as sorm_r
from customer_comments.views import router as custocomm_rt
from customer_contract.views import router as custocontr_rt
from customers_duplicates.views import router as dup_rt
from customers.views import router as customers_router
from services.views import router as srv_rt
from radiusapp.views import router as radius_rt
from tasks.views import router as tasks_rt
from djing2.views import router as root_rt
from groupapp.views import router as groups_rt
from gateways.views import router as gw_rt


router = APIRouter(
    prefix='/api',
    default_response_class=CompatibleJSONResponse,
)

router.include_router(addrs_router)
router.include_router(sorm_r)
router.include_router(custocomm_rt)
router.include_router(custocontr_rt)
router.include_router(dup_rt)
router.include_router(radius_rt)
router.include_router(customers_router)
router.include_router(srv_rt)
router.include_router(tasks_rt)
router.include_router(groups_rt)
router.include_router(gw_rt)
router.include_router(root_rt)
