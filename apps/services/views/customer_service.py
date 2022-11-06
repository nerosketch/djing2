from django.contrib.sites.models import Site
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.utils import get_object_or_404
from fastapi import APIRouter, Depends, Response
from starlette import status
from customers.views.view_decorators import catch_customers_errs
from customers.models import Customer
from services import schemas
from services import models

router = APIRouter(
    prefix='/customer_service',
    tags=['CustomerService'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/service_type_report/',
            response_model=schemas.CustomerServiceTypeReportResponseSchema,
            dependencies=[Depends(permission_check_dependency(
                perm_codename='services.can_view_service_type_report'
            ))]
            )
def service_type_report():
    r = models.CustomerService.objects.customer_service_type_report()
    return r


@router.get('/{customer_id}/current_service/', responses={
    status.HTTP_204_NO_CONTENT: {'description': 'Customer has no service'},
    status.HTTP_200_OK: {'description': 'Customer service details'}
}, response_model=schemas.DetailedCustomerServiceModelSchema)
@catch_customers_errs
def get_current_service(customer_id: int,
                        curr_site: Site = Depends(sites_dependency),
                        auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                        ):
    curr_user, token = auth

    customers_queryset = general_filter_queryset(
        qs_or_model=Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )
    if not customer.current_service:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    curr_srv = customer.current_service
    return schemas.DetailedCustomerServiceModelSchema.from_orm(curr_srv)


@router.get('/activity_report/',
            response_model=schemas.ActivityReportResponseSchema,
            dependencies=[Depends(permission_check_dependency(
                perm_codename='customers.can_view_activity_report'
            ))]
            )
def get_activity_report():
    r = models.Customer.objects.activity_report()
    return r
