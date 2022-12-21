from django.db.models import Count, QuerySet
from django.db import transaction
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CRUDReadGenerator
from djing2.lib.fastapi.general_filter import general_prepare_queryset_dependency
from fastapi import APIRouter, Depends, Path
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


router.include_router(CRUDReadGenerator(
    schema=schemas.BasePaymentModelSchema,
    queryset=BasePaymentModel.objects.order_by('id').annotate(
        pay_count=Count("basepaymentlogmodel")
    ),
))


@router.patch('/{payment_id}/',
              response_model=schemas.BasePaymentModelSchema)
def update_base_payment_model(
    payload: schemas.BasePaymentBaseSchema,
    payment_id: int = Path(gt=0),
    qs: QuerySet = Depends(general_prepare_queryset_dependency(
        perm_codename='fin_app.view_basepaymentmodel',
        qs_or_model=BasePaymentModel
    ))
):
    qs = qs.filter(pk=payment_id)
    sites = payload.sites
    with transaction.atomic():
        qs.update(**payload.dict(
            exclude_unset=True,
            exclude={'sites'}
        ))
        instance = qs.first()
        if sites:
            instance.sites.set(sites)
    return schemas.BasePaymentModelSchema.from_orm(instance)


router.include_router(CRUDReadGenerator(
    schema=schemas.BasePaymentLogModelSchema,
    queryset=BasePaymentLogModel.objects.all(),
    get_one_route=False
), prefix='/base/log')
