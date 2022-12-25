from fastapi import APIRouter
from .base import router as base_rt
from .rncb import router as rncb_rt


router = APIRouter(
    prefix='/fin',
    tags=['Payments'],
)
router.include_router(base_rt)
router.include_router(rncb_rt)
