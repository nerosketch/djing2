from fastapi import APIRouter, Depends
from djing2.lib.fastapi.auth import token_auth_dep
from addresses.views import router as addrs_router


router = APIRouter(
    prefix='/api',
    dependencies=[Depends(token_auth_dep)]
)

router.include_router(addrs_router)
