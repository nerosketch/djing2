from django.contrib.sites.models import Site
from django.utils.translation import gettext
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.utils import get_object_or_404
from fastapi import APIRouter, Depends, Response
from starlette import status
from customers.views.view_decorators import catch_customers_errs
from customers.models import Customer
from profiles.models import UserProfile
from services import schemas
from services import models
from services.models import Service

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

    customer_service_qs = general_filter_queryset(
        qs_or_model=models.CustomerService,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='services.view_customerservice'
    )
    try:
        customer_service = customer_service_qs.select_related('service').get(
            customer_id=customer_id
        )
        return schemas.DetailedCustomerServiceModelSchema.from_orm(customer_service)
    except models.CustomerService.DoesNotExist:
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/activity_report/',
            response_model=schemas.ActivityReportResponseSchema,
            dependencies=[Depends(permission_check_dependency(
                perm_codename='customers.can_view_activity_report'
            ))]
            )
def get_activity_report():
    r = models.CustomerService.objects.activity_report()
    return r


@router.post('/{customer_id}/pick_service/', responses={
    status.HTTP_200_OK: {
        'description': 'Service successfully picked'
    },
    status.HTTP_402_PAYMENT_REQUIRED: {
        'description': gettext('Your account have not enough money')
    }
})
@catch_customers_errs
def customer_pick_service(customer_id: int, payload: schemas.PickServiceRequestSchema,
                          curr_site: Site = Depends(sites_dependency),
                          curr_user: UserProfile = Depends(permission_check_dependency(
                              perm_codename='customers.can_buy_service'
                          )),
                          ):
    """Trying to buy a service if enough money."""

    customers_queryset = general_filter_queryset(
        qs_or_model=Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    )
    customer = get_object_or_404(customers_queryset, pk=customer_id)
    service_queryset = general_filter_queryset(
        qs_or_model=Service,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='services.view_service'
    )
    srv = get_object_or_404(service_queryset, pk=payload.service_id)

    log_comment = gettext("Service '%(service_name)s' has connected via admin until %(deadline)s") % {
        "service_name": srv.title,
        "deadline": payload.deadline,
    }
    try:
        srv.pick_service(
            customer=customer,
            author=curr_user,
            comment=log_comment,
            deadline=payload.deadline,
            allow_negative=True
        )
    except models.NotEnoughMoney as e:
        return Response(str(e), status_code=status.HTTP_402_PAYMENT_REQUIRED)
    return Response('Ok', status_code=status.HTTP_200_OK)


@router.get('/{customer_id}/stop_service/',
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {'description': 'Ok'},
                status.HTTP_418_IM_A_TEAPOT: {
                    'description': 'Service not connected. Nothing to stop'
                }
            })
@catch_customers_errs
def stop_service(customer_id: int,
                 curr_site: Site = Depends(sites_dependency),
                 curr_user: UserProfile = Depends(permission_check_dependency(
                     perm_codename='customers.can_complete_service'
                 ))
                 ):
    customers_queryset = general_filter_queryset(
        qs_or_model=Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.can_complete_service'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )
    cust_srv = customer.active_service()
    if cust_srv is None:
        return Response(
            gettext("Service not connected"),
            status_code=status.HTTP_418_IM_A_TEAPOT
        )
    srv = cust_srv.service
    if srv is None:
        return Response(
            "Custom service has not service (Look at customers.views.admin_site)",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    customer.stop_service(curr_user)
