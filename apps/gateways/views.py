from django.contrib.messages.api import MessageFailure
from django.contrib.sites.models import Site
from django.db.models import Count, Q
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import Pagination
from starlette import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from gateways.models import Gateway, GatewayClassChoices
from gateways.serializers import GatewayModelSerializer
from profiles.models import UserProfileLogActionType, BaseAccount
from fastapi import APIRouter, Depends, Request
from gateways import schemas


router = APIRouter(
    prefix='/gateways',
    tags=['Gateways'],
    dependencies=[Depends(is_admin_auth_dependency)],
)


@router.get('/')
@paginate_qs_path_decorator(
    schema=schemas.GatewayModelSchema,
    db_model=Gateway
)
def get_all_gateways(request: Request,
                     curr_site: Site = Depends(sites_dependency),
                     curr_user: BaseAccount = Depends(permission_check_dependency(
                         perm_codename='customers.change_customer'
                     )),
                     pagination: Pagination = Depends(),
                     ):
    queryset = Gateway.objects.annotate(
        customer_count=Count("customer"),
        customer_count_active=Count("customer", filter=Q(customer__is_active=True)),
        customer_count_w_service=Count(
            "customer", filter=Q(customer__is_active=True) & ~Q(customer__current_service=None)
        ),
    )
    queryset = general_filter_queryset(
        qs_or_model=queryset,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='gateways.view_gateway'
    )
    return queryset


class GatewayModelViewSet(DjingModelViewSet):
    serializer_class = GatewayModelSerializer

    @action(detail=False)
    def fetch_customers_srvnet_credentials_by_gw(self, request, *args, **kwargs):
        gw_id = safe_int(request.query_params.get("gw_id"))
        if gw_id > 0:
            res = Gateway.get_user_credentials_by_gw(gw_id=gw_id)
            res = tuple(res)
            # res = (customer_id, lease_id, lease_time, lease_mac, ip_address,
            #  speed_in, speed_out, speed_burst, service_start_time,
            #  service_deadline)
            return Response(res)
        return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except MessageFailure as msg:
            return Response(str(msg), status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except MessageFailure as msg:
            return Response(str(msg), status=status.HTTP_403_FORBIDDEN)

    def perform_create(self, serializer, *args, **kwargs):
        gw = super().perform_create(serializer=serializer, sites=[self.request.site])
        if gw is not None:
            # log about creating new Gateway
            self.request.user.log(
                do_type=UserProfileLogActionType.CREATE_NAS,
                additional_text='"%(title)s", %(ip)s, %(type)s'
                % {"title": gw.title, "ip": gw.ip_address, "type": gw.get_gw_type_display()},
            )
        return gw

    def perform_destroy(self, instance):
        self.request.user.log(
            do_type=UserProfileLogActionType.DELETE_NAS,
            additional_text='"%(title)s", %(ip)s, %(type)s'
            % {"title": instance.title, "ip": instance.ip_address, "type": instance.get_gw_type_display()},
        )
        return super().perform_destroy(instance)


@router.get('/gateway_class_choices/',
            response_model=list[schemas.GwClassChoice])
def gateway_class_choices():
    gwchoices = (schemas.GwClassChoice(v=k, t=v) for k, v in GatewayClassChoices.choices)
    return gwchoices
