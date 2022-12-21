from fastapi import APIRouter
from .base import router as base_rt


router = APIRouter(
    prefix='/fin',
    tags=['Payments'],
)
router.include_router(base_rt)
