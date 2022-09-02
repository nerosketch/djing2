from fastapi import APIRouter, Depends
from djing2.lib.fastapi.auth import token_auth_dep
from addresses.views import router as addrs_router
from sorm_export.views import router as sorm_r


router = APIRouter(
    prefix='/api',
    dependencies=[Depends(token_auth_dep)]
)

router.include_router(addrs_router)
router.include_router(sorm_r)
