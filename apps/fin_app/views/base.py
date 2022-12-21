from django.db.models import Count
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter, CRUDReadGenerator
from fastapi import APIRouter, Depends
from fin_app.models.base_payment_model import (
    BasePaymentModel,
    BasePaymentLogModel,
    report_by_pays
)
from fin_app.schemas import base as schemas


router = APIRouter(
    prefix='/base',
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/pays_report/',
            response_model=list[schemas.PaysReportResponseSchema],
            response_model_exclude_none=True)
def pays_report(params: schemas.PaysReportParamsSchema = Depends()):
    return report_by_pays(
        params=params
    )


router.include_router(CrudRouter(
    schema=schemas.BasePaymentModelSchema,
    update_schema=schemas.BasePaymentBaseSchema,
    queryset=BasePaymentModel.objects.order_by('id').annotate(
        pay_count=Count("basepaymentlogmodel")
    ),
    create_route=False
))


router.include_router(CRUDReadGenerator(
    schema=schemas.BasePaymentLogModelSchema,
    queryset=BasePaymentLogModel.objects.all(),
    get_one_route=False
), prefix='/base/log')
