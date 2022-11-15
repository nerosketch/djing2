from fastapi import APIRouter
from .admin_side import router as admrt
from .user_side import router as usrt


router = APIRouter(
    prefix='/customers',
)

router.include_router(usrt)
router.include_router(admrt)
