from datetime import datetime
from typing import Optional

from customers import models
from customers.views.view_decorators import catch_customers_errs
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Count, Q
from django.utils.translation import gettext
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE, is_superuser_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency, check_perm, filter_qs_by_rights
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination, NOT_FOUND
from djing2.lib.fastapi.utils import get_object_or_404, AllOptionalMetaclass, create_get_initial_route
from djing2.lib.filters import filter_qs_by_fields_dependency
from djing2.lib.filters import search_qs_by_fields_dependency
from dynamicfields.views import AbstractDynamicFieldContentModelViewSet
from fastapi import APIRouter, Depends, Request, Response, Body, Query, UploadFile, Form
from groupapp.models import Group
from profiles.models import UserProfileLogActionType, UserProfile
from profiles.schemas import generate_random_password
from rest_framework.authtoken.models import Token
from services.models import Service
from starlette import status

from .. import schemas

# TODO:
#  добавить новые права где не хватает.
#  проверить чтоб нельзя было изменить некоторые поля из api (типо изменить CustomerService и врубить себе услугу).


router = APIRouter(
    prefix='',
    tags=['Customers'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/customer-log/', response_model=IListResponse[schemas.CustomerLogModelSchema],
            response_model_exclude_none=True
            )
@paginate_qs_path_decorator(schema=schemas.CustomerLogModelSchema, db_model=models.CustomerLog)
def get_customer_payment_log(request: Request,
                             customer: int,
                             curr_site: Site = Depends(sites_dependency),
                             auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                             pagination: Pagination = Depends()):
    curr_user, token = auth

    customers_qs = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='customers.view_customer'
    ).filter(pk=customer)
    if not customers_qs.exists():
        return models.CustomerLog.objects.empty()
    del customers_qs

    qs = models.CustomerLog.objects.filter(
        customer_id=customer
    ).select_related('author').order_by('-id')
    return qs


@router.get('/groups_with_customers/', response_model=list[schemas.GroupsWithCustomersSchema])
def groups_with_customers(
    curr_site: Site = Depends(sites_dependency),
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
):
    # TODO: Also filter by address
    curr_user, token = auth

    grps = general_filter_queryset(
        qs_or_model=Group,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='groupapp.view_group'
    ).annotate(
        customer_count=Count('customer')
    ).filter(
        customer_count__gt=0
    ).order_by('title')
    return (schemas.GroupsWithCustomersSchema.from_orm(grp) for grp in grps.iterator())


@router.get('/service_users/', response_model=list[schemas.ServiceUsersResponseSchema])
@catch_customers_errs
def get_service_users(service_id: int,
                      curr_site: Site = Depends(sites_dependency),
                      auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                      ):
    curr_user, token = auth
    qs = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    )
    qs = qs.filter(current_service__service_id=service_id)
    qs = qs.values("id", "group_id", "username", "fio")
    return (schemas.ServiceUsersResponseSchema(**v) for v in qs)


@router.post('/set_service_group_accessory/', status_code=status.HTTP_204_NO_CONTENT)
@catch_customers_errs
def set_service_group_accessory(payload: schemas.SetServiceGroupAccessoryRequestSchema,
                                curr_site: Site = Depends(sites_dependency),
                                curr_user: UserProfile = Depends(permission_check_dependency(
                                    perm_codename='customers.change_customer'
                                ))
                                ):
    groups_queryset = general_filter_queryset(
        qs_or_model=Group,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='groupapp.view_group'
    )
    group = get_object_or_404(groups_queryset, pk=payload.group_id)
    models.Customer.set_service_group_accessory(
        group,
        payload.services,
        current_site=curr_site,
        current_user=curr_user
    )


@router.get('/filter_device_port/',
            response_model_exclude={'password'},
            response_model=list[schemas.CustomerModelSchema])
@catch_customers_errs
def filter_device_port(device_id: int, port_id: int,
                       curr_site: Site = Depends(sites_dependency),
                       auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                       ):
    curr_user, token = auth

    customers = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    ).filter(
        device_id=device_id,
        dev_port_id=port_id
    )
    return (schemas.CustomerModelSchema.from_orm(c) for c in customers.iterator())


@router.get('/generate_password/', response_model=str)
def generate_password_for_customer():
    rp = generate_random_password()
    return rp


@router.get('/get_afk/', response_model=IListResponse[schemas.GetAfkResponseSchema])
def get_afk(date_limit: datetime,
            locality: int = 0,
            out_limit: int = 50):
    # FIXME: отсюда можно увидеть слишком много учёток без прав. Надо ограничить правом.

    afk = models.Customer.objects.filter_long_time_inactive_customers(
        date_limit=date_limit,
        out_limit=out_limit
    )
    if locality > 0:
        addr_filtered_customers = models.Customer.objects.filter_customers_by_address(
            addr_id=locality
        ).only('pk').values_list('pk', flat=True)
        afk = tuple(c for c in afk if c.customer_id in addr_filtered_customers)
        del addr_filtered_customers

    res_afk = (schemas.GetAfkResponseSchema(
        timediff=str(r.timediff),
        last_date=r.last_date,
        customer_id=r.customer_id,
        customer_uname=r.customer_uname,
        customer_fio=r.customer_fio
    ) for r in afk)
    return Response({
        'count': 1,
        'next': None,
        'previous': None,
        'results': res_afk
    })


class CustomerResponseModelSchema(schemas.CustomerModelSchema, metaclass=AllOptionalMetaclass):
    id: Optional[int] = None
    username: Optional[str] = None


@router.get('/bums/',
            response_model_exclude={'password'},
            response_model_exclude_none=True,
            response_model=IListResponse[CustomerResponseModelSchema]
            )
@paginate_qs_path_decorator(schema=CustomerResponseModelSchema, db_model=models.Customer)
def get_customers_bums(
    curr_site: Site = Depends(sites_dependency),
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
):
    """Customers without addresses."""

    curr_user, token = auth
    customers_queryset = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    ).filter(address=None)
    return customers_queryset


router.include_router(CrudRouter(
    schema=schemas.InvoiceForPaymentModelSchema,
    create_schema=schemas.InvoiceForPaymentBaseSchema,
    update_schema=schemas.InvoiceForPaymentBaseSchema,
    queryset=models.InvoiceForPayment.objects.select_related("customer", "author"),
), prefix='/invoices')

router.include_router(CrudRouter(
    schema=schemas.CustomerRawPasswordModelSchema,
    update_schema=schemas.CustomerRawPasswordBaseSchema,
    queryset=models.CustomerRawPassword.objects.select_related("customer"),
    create_route=False,
    get_all_route=False,
    delete_one_route=False
), prefix='/customer-raw-password')

router.include_router(CrudRouter(
    schema=schemas.AdditionalTelephoneModelSchema,
    create_schema=schemas.AdditionalTelephoneBaseSchema,
    queryset=models.AdditionalTelephone.objects.defer("customer"),
    get_all_route=False,
    get_one_route=False
), prefix='/additional-telephone')


@router.get(
    '/additional-telephone/',
    response_model=IListResponse[schemas.AdditionalTelephoneModelSchema]
)
@paginate_qs_path_decorator(
    schema=schemas.AdditionalTelephoneModelSchema,
    db_model=models.AdditionalTelephone
)
def get_additional_telephones(request: Request, customer: int,
                              auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                              pagination: Pagination = Depends()
                              ):
    curr_user, token = auth
    rqs = filter_qs_by_rights(
        qs_or_model=models.AdditionalTelephone,
        curr_user=curr_user,
        perm_codename='customers.view_additionaltelephone'
    )
    return rqs.filter(customer_id=customer)


@router.get('/attach_group_service/', response_model=list[schemas.AttachGroupServiceResponseSchema])
def attach_group_service_get(group: int,
                             curr_site: Site = Depends(sites_dependency),
                             auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                             ):
    """Shows how services available in group"""

    curr_user, token = auth

    groups_qs = general_filter_queryset(
        qs_or_model=Group,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='groupapp.view_group'
    )
    grp = get_object_or_404(groups_qs, pk=group)

    selected_services_id = tuple(pk[0] for pk in grp.service_set.only("pk").values_list("pk"))

    services_qs = general_filter_queryset(
        qs_or_model=Service,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='services.view_service'
    )
    services_qs = services_qs.only("pk", "title").iterator()

    return (schemas.AttachGroupServiceResponseSchema(
        service=srv.pk,
        service_name=srv.title,
        check=srv.pk in selected_services_id
    ) for srv in services_qs)


@router.post('/attach_group_service/', status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def attach_group_service(request_data: list[schemas.AttachGroupServiceResponseSchema], group: int,
                         curr_site: Site = Depends(sites_dependency),
                         curr_user: UserProfile = Depends(permission_check_dependency(
                             perm_codename='groupapp.change_group'
                         ))
                         ):
    groups_qs = general_filter_queryset(
        qs_or_model=Group,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='groupapp.change_group'
    )
    group = get_object_or_404(groups_qs, pk=group)
    del groups_qs
    # selected_service_ids_db = frozenset(t.pk for t in group.service_set.only('pk'))

    service_qs = general_filter_queryset(
        qs_or_model=Service,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='services.view_service'
    )
    all_available_service_ids_db = frozenset(srv.pk for srv in service_qs.only("pk").iterator())
    del service_qs

    # list of dicts: service<int>, check<bool>
    selected_service_ids = frozenset(
        s.service
        for s in request_data
        if s.check and s.service in all_available_service_ids_db
    )

    group.service_set.set(selected_service_ids)
    return


@router.delete('/attachments/{attachment_id}/',
               status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_attachment(attachment_id: int,
                               curr_user: UserProfile = Depends(permission_check_dependency(
                                   perm_codename='customers.delete_customerattachment'
                               ))
                               ):
    qs = filter_qs_by_rights(
        qs_or_model=models.CustomerAttachment,
        curr_user=curr_user,
        perm_codename='customers.delete_customerattachment'
    ).filter(pk=attachment_id)
    if not qs.exists():
        raise NOT_FOUND
    qs.delete()


@router.get('/attachments/',
            response_model=list[schemas.CustomerAttachmentModelSchema],
            dependencies=[Depends(permission_check_dependency(
                perm_codename='customers.view_customerattachment'
            ))]
            )
def get_customer_attachments(
    customer_id: int = Query(gt=0, title='Customer id for filter documents by customer'),
):
    qs = models.CustomerAttachment.objects.select_related(
        "author", "customer"
    ).filter(
        customer_id=customer_id
    )

    return (schemas.CustomerAttachmentModelSchema(
        id=a.pk,
        create_time=a.create_time,
        author_id=a.author_id,
        author_name=a.author.get_full_name(),
        customer_id=a.customer_id,
        customer_name=a.customer.get_full_name(),
        title=a.title,
        doc_file=a.doc_file.url,
    ) for a in qs)


@router.post('/attachments/',
             response_model=schemas.CustomerAttachmentModelSchema,
             status_code=status.HTTP_201_CREATED)
def create_customer_attachment(
    doc_file: UploadFile,
    title: str = Form(),
    customer_id: int = Form(),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='customers.add_customerattachment'
    ))
):
    from django.core.files.base import ContentFile

    cf = ContentFile(doc_file.file._file.read(), name=doc_file.filename)
    obj = models.CustomerAttachment.objects.create(
        title=title,
        customer_id=customer_id,
        author_id=curr_user.pk,
        doc_file=cf
    )
    return schemas.CustomerAttachmentModelSchema(
        id=obj.pk,
        create_time=obj.create_time,
        author_id=obj.author_id,
        author_name=obj.author.get_full_name(),
        customer_id=obj.customer_id,
        customer_name=obj.customer.get_full_name(),
        title=obj.title,
        doc_file=obj.doc_file.url,
    )


class CustomerDynamicFieldContentModelViewSet(AbstractDynamicFieldContentModelViewSet):
    queryset = models.CustomerDynamicFieldContentModel.objects.select_related('field')

    def get_group_id(self) -> int:
        customer_id = self.request.query_params.get('customer')
        self.customer_id = customer_id
        customer = get_object_or_404(models.Customer.objects.only('group_id'), pk=customer_id)
        self.customer = customer
        return customer.group_id

    def filter_content_fields_queryset(self):
        return self.get_queryset().filter(
            customer_id=self.customer_id,
        )

    def create_content_field_kwargs(self, field_data):
        if hasattr(self, 'customer_id'):
            return {
                'customer_id': self.customer_id
            }
        return {
            'customer_id': field_data.get('customer')
        }


create_get_initial_route(
    router=router,
    schema=schemas.CustomerSchema
)


@router.get('/customer-token/',
            response_model=schemas.TokenResponseSchema,
            dependencies=[Depends(is_superuser_auth_dependency)])
def super_user_get_customer_token_by_phone(data: schemas.TokenRequestSchema):
    tel = data.telephone

    #  customers = models.Customer.objects.filter(telephone=)
    tel = models.AdditionalTelephone.objects.filter(
        Q(telephone=tel), Q(customer__telephone=tel)
    ).select_related('customer').first()
    if tel:
        user = tel.customer
        token = Token.objects.filter(user=user).first()
        if token:
            return schemas.TokenResponseSchema(
                token=token.key
            )
    return schemas.TokenResponseSchema(
        token=None
    )


@router.get(
    '/{customer_id}/ping_all_ips/',
    response_model=schemas.TypicalResponse,
)
@catch_customers_errs
def ping_all_ips(customer_id: int,
                 curr_site: Site = Depends(sites_dependency),
                 curr_user: UserProfile = Depends(permission_check_dependency(
                     perm_codename='customers.can_ping'
                 ))
                 ):
    customers_queryset = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )
    res_text, res_status = customer.ping_all_leases()
    return schemas.TypicalResponse(
        text=res_text,
        status=res_status
    )


@router.post('/{customer_id}/add_balance/')
@catch_customers_errs
def add_balance(customer_id: int,
                payload: schemas.AddBalanceRequestSchema,
                curr_site: Site = Depends(sites_dependency),
                curr_user: UserProfile = Depends(permission_check_dependency(
                    perm_codename='customers.can_add_balance'
                ))
                ):
    cost = payload.cost
    if cost < 0.0:
        check_perm(
            user=curr_user,
            perm_codename='customers.can_add_negative_balance'
        )

    customers_queryset = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.change_customer'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )
    comment = payload.comment
    customer.add_balance(
        profile=curr_user,
        cost=cost,
        comment=comment or gettext("fill account through admin side"),
    )
    return Response()


@router.put('/{customer_id}/passport/',
            response_model=schemas.PassportInfoModelSchema,
            responses={
                status.HTTP_200_OK: {'description': 'Updated existed passport instance'},
                status.HTTP_201_CREATED: {'description': 'Created new passport instance'}
            }
            )
@catch_customers_errs
def set_customer_passport(response: Response,
                          customer_id: int, payload: schemas.PassportInfoBaseSchema,
                          curr_site: Site = Depends(sites_dependency),
                          auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                          ):
    curr_user, token = auth

    customers_queryset = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )
    del customers_queryset

    passport_obj = models.PassportInfo.objects.filter(customer_id=customer_id).first()

    data_dict = payload.dict(
        exclude_unset=True,
    )

    if passport_obj is None:
        # create passport info for customer
        passport_obj = models.PassportInfo.objects.create(
            customer=customer,
            **data_dict
        )
        response.status_code = status.HTTP_201_CREATED
    else:
        # change passport info for customer
        for f_name, f_val in data_dict.items():
            setattr(passport_obj, f_name, f_val)
        passport_obj.save()
        response.status_code = status.HTTP_200_OK

    return schemas.PassportInfoModelSchema.from_orm(passport_obj)


@router.get('/{customer_id}/passport/',
            response_model=schemas.PassportInfoModelSchema
            )
def get_customer_passport(
    customer_id: int,
    curr_site: Site = Depends(sites_dependency),
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)

):
    curr_user, token = auth

    customers_queryset = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    ).filter(pk=customer_id)

    passport_obj = get_object_or_404(models.PassportInfo, customer_id__in=customers_queryset)
    return schemas.PassportInfoModelSchema.from_orm(passport_obj)


@router.get('/{customer_id}/is_access/',
            response_model=bool,
            responses={
                status.HTTP_200_OK: {
                    'description': 'Shows is customer has access to any service'
                },
                status.HTTP_404_NOT_FOUND: {
                    'description': 'Customer does not exists'
                }
            })
def get_customer_is_access(customer_id: int,
                           curr_site: Site = Depends(sites_dependency),
                           auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                           ):
    curr_user, token = auth
    customers_queryset = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )
    return customer.is_access()


@router.post('/{customer_id}/set_markers/', responses={
    status.HTTP_400_BAD_REQUEST: {
        'description': 'Bad flag names in body'
    },
    status.HTTP_204_NO_CONTENT: {
        'description': 'Markers applied successfully'
    }
})
def set_customer_markers(customer_id: int,
                         flag_names: list[str] = Body(title='Flag name list'),
                         curr_site: Site = Depends(sites_dependency),
                         curr_user: UserProfile = Depends(permission_check_dependency(
                             perm_codename='customers.change_customer'
                         ))
                         ):
    customers_queryset = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.change_customer'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )
    _mflags = tuple(f for f, n in models.Customer.MARKER_FLAGS)
    for flag_name in flag_names:
        if flag_name not in _mflags:
            return Response(
                'Bad "flags". Must be an array of flag names. Such as %s' % _mflags,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    customer.set_markers(flag_names=flag_names)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch('/{customer_id}/', response_model_exclude={'password'},
              response_model=schemas.CustomerModelSchema)
def update_customer_profile(customer_id: int,
                            customer_data: schemas.CustomerSchema,
                            curr_site: Site = Depends(sites_dependency),
                            curr_user: UserProfile = Depends(
                                permission_check_dependency(perm_codename='customers.change_customer')
                            )):
    customers_qs = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='customers.change_customer'
    )
    acc = get_object_or_404(customers_qs, pk=customer_id)

    pdata = customer_data.dict(exclude_unset=True)
    raw_password = pdata.pop('password', None)

    # TODO: deny changing sites without special permission
    sites = pdata.pop('sites', None)

    for d_name, d_val in pdata.items():
        setattr(acc, d_name, d_val)

    if isinstance(sites, (tuple, list)):
        acc.sites.set(sites)

    if raw_password:
        schemas.update_passw(acc=acc, raw_password=raw_password)
        acc.set_password(raw_password)

    acc.save(update_fields=[d_name for d_name, d_val in pdata.items()] + ['password'])
    return schemas.CustomerModelSchema.from_orm(acc)


@router.get('/{customer_id}/', response_model=schemas.CustomerModelSchema,
            response_model_exclude={'password'})
def get_customer_profile(customer_id: int,
                         curr_site: Site = Depends(sites_dependency),
                         auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                         ):
    curr_user, token = auth
    customers_qs = general_filter_queryset(
        qs_or_model=models.Customer,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='customers.view_customer'
    )
    acc = get_object_or_404(customers_qs, pk=customer_id)
    return schemas.CustomerModelSchema.from_orm(acc)


@router.delete('/{customer_id}/', status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_customer(customer_id: int,
                    curr_site: Site = Depends(sites_dependency),
                    curr_user: UserProfile = Depends(permission_check_dependency(
                        perm_codename='customers.delete_customer'
                    ))
                    ):
    queryset = general_filter_queryset(
        qs_or_model=models.Customer.objects.all(),
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.delete_customer'
    )
    instance = get_object_or_404(queryset=queryset, pk=customer_id)

    with transaction.atomic():
        # log about deleting customer
        curr_user.log(
            do_type=UserProfileLogActionType.DELETE_USER,
            additional_text=(
                '%(uname)s, "%(fio)s", %(addr)s' % {
                    "uname": instance.username,
                    "fio": instance.fio or "-",
                    "addr": instance.full_address,
                }
            ).strip(),
        )
        instance.delete()


@router.post('/', response_model_exclude={'password'},
             response_model=schemas.CustomerModelSchema,
             status_code=status.HTTP_201_CREATED)
def create_customer_profile(new_customer_data: schemas.CustomerSchema,
                            curr_site: Site = Depends(sites_dependency),
                            curr_user: UserProfile = Depends(permission_check_dependency(
                                perm_codename='customers.add_customer'
                            ))
                            ):
    pdata = new_customer_data.dict(exclude_unset=True)
    pdata.update({
        "is_admin": False,
        "is_superuser": False
    })
    with transaction.atomic():
        acc = models.Customer.objects.create(**pdata)
        acc.sites.add(curr_site)
        raw_password = new_customer_data.password
        schemas.update_passw(acc, raw_password=raw_password)
        if acc:
            # log about creating new customer
            curr_user.log(
                do_type=UserProfileLogActionType.CREATE_USER,
                additional_text='%s, "%s", %s' % (
                    acc.username,
                    acc.fio,
                    acc.group.title if acc.group_id else "",
                ),
            )
    return schemas.CustomerModelSchema.from_orm(acc)


@router.get('/', response_model_exclude={'password'},
            response_model=IListResponse[CustomerResponseModelSchema],
            response_model_exclude_none=True
            )
@paginate_qs_path_decorator(schema=CustomerResponseModelSchema, db_model=models.Customer)
def get_customers(request: Request,
                  street: Optional[int] = None, house: Optional[int] = None,
                  address: Optional[int] = None,
                  curr_site: Site = Depends(sites_dependency),
                  auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                  filter_fields_q: Q = Depends(filter_qs_by_fields_dependency(
                      fields={
                          'group': int, 'device': int, 'dev_port': int, 'current_service__service': int,
                          'birth_day': datetime, 'is_active': bool
                      },
                      db_model=models.Customer
                  )),
                  search_filter_q: Q = Depends(search_qs_by_fields_dependency(
                      search_fields=["username", "fio", "telephone", "description"]
                  )),
                  pagination: Pagination = Depends()
                  ):
    curr_user, token = auth

    _customer_base_query = models.Customer.objects.select_related(
        "current_service", "current_service__service", "group",
        "address", "address__parent_addr"
    )

    queryset = general_filter_queryset(
        qs_or_model=_customer_base_query,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_customer'
    )

    queryset = queryset.filter(filter_fields_q | search_filter_q)

    if house:
        return queryset.filter_customers_by_address(
            addr_id=house,
        )
    else:
        if street:
            return queryset.filter_customers_by_address(
                addr_id=street,
            )

    if address:
        return queryset.filter_customers_by_address(
            addr_id=address,
        )

    return queryset
