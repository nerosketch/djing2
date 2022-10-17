from typing import Optional
from datetime import datetime

from customers import models, serializers
from customers.views.view_decorators import catch_customers_errs
from django.contrib.auth.hashers import make_password
from django.db.models import Count, Q
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE, is_superuser_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency, check_perm
from djing2.lib.fastapi.types import IListResponse, Pagination
from djing2.lib.fastapi.utils import get_object_or_404, AllOptionalMetaclass
from djing2.lib.filters import search_qs_by_fields_dependency
from djing2.lib.filters import filter_qs_by_fields_dependency
from dynamicfields.views import AbstractDynamicFieldContentModelViewSet
from fastapi import APIRouter, Depends, Request, Response, Body
from starlette import status
from groupapp.models import Group
from guardian.shortcuts import get_objects_for_user
from profiles.models import UserProfileLogActionType, UserProfile
from rest_framework.authtoken.models import Token
from services.models import OneShotPay, PeriodicPay, Service

from .. import schemas

# TODO:
#  выставить везде права.
#  добавить новые права где не хватает.
#  фильтровать по сайтам.
#  проверить чтоб нельзя было изменить некоторые поля из api (типо изменить CustomerService и врубить себе услугу).


router = APIRouter(
    prefix='/customers',
    tags=['customers'],
    dependencies=[Depends(is_admin_auth_dependency)]
)

router.include_router(CrudRouter(
    schema=schemas.CustomerServiceModelSchema,
    create_schema=schemas.CustomerServiceBaseSchema,
    queryset=models.CustomerService.objects.all(),
    create_route=False,
    delete_one_route=False,
    update_route=False
), prefix='/customer-service')

router.include_router(CrudRouter(
    schema=schemas.CustomerLogModelSchema,
    queryset=models.CustomerLog.objects.select_related(
        "customer",
        "author"
    ).order_by('-id'),
    create_route=False,
    delete_one_route=False,
    update_route=False
), prefix='/customer-log')

_customer_base_query = models.Customer.objects.select_related(
    "current_service", "current_service__service", "gateway"
)


@router.post('/', response_model_exclude={'password'}, response_model=schemas.CustomerModelSchema)
def create_customer_profile(new_customer_data: schemas.CustomerSchema):
    pdata = new_customer_data.dict()
    pdata.update({
        "is_admin": False,
        "is_superuser": False
    })
    acc = models.Customer.objects.create(**pdata)
    raw_password = new_customer_data.password
    schemas.update_passw(acc, raw_password=raw_password)
    return schemas.CustomerModelSchema.from_orm(acc)


@router.get('/groups_with_customers/', response_model=list[schemas.GroupsWithCustomersSchema])
def groups_with_customers():
    # TODO: Also filter by address
    grps = Group.objects.annotate(
        customer_count=Count('customer')
    ).filter(
        customer_count__gt=0
    ).order_by('title')
    return [schemas.GroupsWithCustomersSchema.from_orm(grp) for grp in grps.iterator()]


@router.patch('/{customer_id}/', response_model_exclude={'password'}, response_model=schemas.CustomerModelSchema)
def update_customer_profile(customer_id: int, customer_data: schemas.CustomerSchema):
    pdata = customer_data.dict(exclude_none=True, exclude_unset=True, exclude_defaults=True)
    raw_password = pdata.pop('password')
    acc = get_object_or_404(models.Customer, pk=customer_id)
    for d_name, d_val in pdata.items():
        setattr(acc, d_name, d_val)
    if raw_password:
        schemas.update_passw(acc=acc, raw_password=raw_password)
        setattr(acc, 'password', make_password(raw_password))

    acc.save(update_fields=[d_name for d_name, d_val in pdata.items()])
    return schemas.CustomerModelSchema.from_orm(acc)


@router.get('/{customer_id}/', response_model=schemas.CustomerModelSchema, response_model_exclude={'password'})
def get_customer_profile(customer_id: int):
    acc = get_object_or_404(models.Customer, pk=customer_id)
    return schemas.CustomerModelSchema.from_orm(acc)


class CustomerResponseModelSchema(schemas.CustomerModelSchema, metaclass=AllOptionalMetaclass):
    pass


@router.get('/', response_model_exclude={'password'},
            response_model=IListResponse[CustomerResponseModelSchema])
@paginate_qs_path_decorator(schema=CustomerResponseModelSchema, db_model=models.Customer)
def get_customers(request: Request,
                  street: Optional[int] = None, house: Optional[int] = None,
                  address: Optional[int] = None,
                  user: UserProfile = Depends(permission_check_dependency(perm_codename='customers.view_customer')),
                  filter_fields_q: Q = Depends(filter_qs_by_fields_dependency(
                      fields={
                          'group': int, 'device': int, 'dev_port': int, 'current_service__service': int,
                          'birth_day': datetime,
                      },
                      db_model=models.Customer
                  )),
                  search_filter_q: Q = Depends(search_qs_by_fields_dependency(
                      search_fields=["username", "fio", "telephone", "description"]
                  )),
                  pagination: Pagination = Depends()
                  ):
    # filter by rights
    queryset = get_objects_for_user(
        user=user,
        perms='customers.view_customer',
        klass=_customer_base_query
    )

    queryset = queryset.filter(filter_fields_q | search_filter_q)

    if house:
        return queryset.filter_customers_by_addr(
            addr_id=house,
        )
    else:
        if street:
            return queryset.filter_customers_by_addr(
                addr_id=street,
            )

    if address:
        return queryset.filter_customers_by_addr(
            addr_id=address,
        )

    # TODO: order by fields
    # TODO: filter by sites

    return queryset


@router.post('/', response_model_exclude={'password'},
             response_model=schemas.CustomerModelSchema,
             status_code=status.HTTP_201_CREATED
             )
def create_customer(payload: schemas.CustomerSchema,
                    curr_user: UserProfile = Depends(permission_check_dependency(
                        perm_codename='customers.add_customer'
                    )),
                    ):
    customer_instance = models.Customer.objects.create(
        **payload.dict(),
        sites=[current_site]
    )
    if customer_instance:
        # log about creating new customer
        curr_user.log(
            do_type=UserProfileLogActionType.CREATE_USER,
            additional_text='%s, "%s", %s'
                            % (
                                customer_instance.username,
                                customer_instance.fio,
                                customer_instance.group.title if customer_instance.group else "",
                            ),
        )
    return schemas.CustomerModelSchema.from_orm(customer_instance)


@router.delete('/{customer_id}/', status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_customer(customer_id: int,
                    curr_user: UserProfile = Depends(permission_check_dependency(
                        perm_codename='customers.delete_customer'
                    ))
                    ):
    # TODO: filter by sites
    queryset = get_objects_for_user(
        user=curr_user,
        perms='customers.delete_customer',
        klass=models.Customer.objects.all()
    )
    instance = get_object_or_404(queryset=queryset, pk=customer_id)

    # log about deleting customer
    curr_user.log(
        do_type=UserProfileLogActionType.DELETE_USER,
        additional_text=(
            '%(uname)s, "%(fio)s", %(addr)s'
            % {
                "uname": instance.username,
                "fio": instance.fio or "-",
                "addr": instance.full_address,
            }
        ).strip(),
    )


@router.post('/{customer_id}/pick_service/', responses={
    status.HTTP_200_OK: {'description': 'Ok'},
    status.HTTP_402_PAYMENT_REQUIRED: {'description': gettext('Your account have not enough money')}
})
@catch_customers_errs
def customer_pick_service(customer_id: int, payload: schemas.PickServiceRequestSchema,
                          curr_user: UserProfile = Depends(permission_check_dependency(
                              perm_codename='customers.can_buy_service'
                          ))
                          ):
    """Trying to buy a service if enough money."""

    srv = get_object_or_404(Service, pk=payload.service_id)
    customer = get_object_or_404(models.Customer, pk=customer_id)
    log_comment = _("Service '%(service_name)s' has connected via admin until %(deadline)s") % {
        "service_name": srv.title,
        "deadline": payload.deadline,
    }
    try:
        customer.pick_service(
            service=srv,
            author=curr_user,
            comment=log_comment,
            deadline=payload.deadline,
            allow_negative=True
        )
    except models.NotEnoughMoney as e:
        return Response(str(e), status_code=status.HTTP_402_PAYMENT_REQUIRED)
    return Response('Ok', status_code=status.HTTP_200_OK)


@router.post('/{customer_id}/make_shot/', responses={
    status.HTTP_403_FORBIDDEN: {'description': 'making payment shot not possible'},
    status.HTTP_200_OK: {'description': 'Ok'}
})
@catch_customers_errs
def make_payment_shot(customer_id: int, payload: schemas.MakePaymentSHotRequestSchema,
                      curr_user: UserProfile = Depends(permission_check_dependency(
                          perm_codename='customers.can_buy_service'
                      ))
                      ):
    customer = get_object_or_404(models.Customer, pk=customer_id)
    shot = get_object_or_404(OneShotPay, pk=payload.shot_id)
    shot.before_pay(customer=customer)
    r = customer.make_shot(shot=shot, user_profile=curr_user, allow_negative=True)
    shot.after_pay(customer=customer)
    if not r:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
    return Response(r)


@router.post('/{customer_id}/make_periodic_pay/', dependencies=[
    Depends(permission_check_dependency(
        perm_codename='customers.can_buy_service'
    ))
])
@catch_customers_errs
def make_periodic_pay(
    customer_id: int,
    payload: schemas.PeriodicPayForIdRequestSchema
):
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )
    periodic_pay = get_object_or_404(
        PeriodicPay,
        pk=payload.periodic_pay_id
    )
    customer.make_periodic_pay(
        periodic_pay=periodic_pay,
        next_pay=payload.next_pay
    )
    return Response("ok")


@router.get('/service_users/', response_model=list[schemas.ServiceUsersResponseSchema])
@catch_customers_errs
def get_service_users(service_id: int,
                      curr_user: UserProfile = Depends(permission_check_dependency(
                          perm_codename='customers.can_buy_service'
                      ))):
    qs = models.Customer.objects.filter(current_service__service_id=service_id)
    if not curr_user.is_superuser:
        qs = qs.filter(sites__in=[curr_site])
    qs = qs.values("id", "group_id", "username", "fio")
    return (schemas.ServiceUsersResponseSchema(**v) for v in qs)


@router.get('/{customer_id}/stop_service/', status_code=status.HTTP_204_NO_CONTENT)
@catch_customers_errs
def stop_service(customer_id: int,
                 curr_user: UserProfile = Depends(permission_check_dependency(
                     perm_codename='customers.can_complete_service'
                 ))
                 ):
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )
    cust_srv = customer.active_service()
    if cust_srv is None:
        return Response(gettext("Service not connected"))
    srv = cust_srv.service
    if srv is None:
        return Response(
            "Custom service has not service (Look at customers.views.admin_site)",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    customer.stop_service(curr_user)


@router.get(
    '/{customer_id}/ping_all_ips/',
    response_model=schemas.TypicalResponse,
    dependencies=[
        Depends(permission_check_dependency(
            perm_codename='customers.can_ping'
        ))
    ])
@catch_customers_errs
def ping_all_ips(customer_id: int):
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )
    res_text, res_status = customer.ping_all_leases()
    return schemas.TypicalResponse(
        text=res_text,
        status=res_status
    )


@router.get('/{customer_id}/current_service/', responses={
    status.HTTP_204_NO_CONTENT: {'description': 'Customer has no service'},
    status.HTTP_200_OK: {'description': 'Customer service details'}
}, response_model=schemas.DetailedCustomerServiceModelSchema)
@catch_customers_errs
def get_current_service(customer_id: int):
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )
    if not customer.current_service:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    curr_srv = customer.current_service
    return schemas.DetailedCustomerServiceModelSchema.from_orm(curr_srv)


@router.post('/{customer_id}/add_balance/')
@catch_customers_errs
def add_balance(customer_id: int,
                payload: schemas.AddBalanceRequestSchema,
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
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )
    comment = payload.comment
    customer.add_balance(
        profile=curr_user,
        cost=cost,
        comment=" ".join(comment.split()) if comment else gettext("fill account through admin side"),
    )
    customer.save(update_fields=("balance",))
    return Response()


@router.post('/set_service_group_accessory/', status_code=status.HTTP_204_NO_CONTENT)
@catch_customers_errs
def set_service_group_accessory(payload: schemas.SetServiceGroupAccessoryRequestSchema,
                                curr_user: UserProfile = Depends(permission_check_dependency(
                                    perm_codename='customers.change_customer'
                                ))
                                ):
    group = get_object_or_404(Group, pk=payload.group_id)
    models.Customer.set_service_group_accessory(
        group,
        payload.services,
        # TODO: передать сайт
        current_site=0,
        current_user=curr_user
    )


@router.get('/filter_device_port/',
            response_model_exclude={'password'},
            response_model=list[schemas.CustomerModelSchema])
@catch_customers_errs
def filter_device_port(device_id: int, port_id: int):
    customers = models.Customer.objects.filter(
        device_id=device_id,
        dev_port_id=port_id
    )
    return (schemas.CustomerModelSchema.from_orm(c) for c in customers.iterator())


@router.put('/{customer_id}/passport/',
            response_model=schemas.PassportInfoModelSchema,
            responses={
                status.HTTP_200_OK: {'description': 'Updated existed passport instance'},
                status.HTTP_201_CREATED: {'description': 'Created new passport instance'}
            }
            )
@catch_customers_errs
def set_customer_passport(customer_id: int, payload: schemas.PassportInfoBaseSchema):
    passport_obj = models.PassportInfo.objects.filter(customer_id=customer_id).first()
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )

    data_dict = payload.dict(
        skip_defaults=True,
        exclude_unset=True,
        exclude_none=True
    )

    if passport_obj is None:
        # create passport info for customer
        passport_obj = models.PassportInfo.objects.create(
            customer=customer,
            **data_dict
        )
        res_stat = status.HTTP_201_CREATED
    else:
        # change passport info for customer
        for f_name, f_val in data_dict.items():
            setattr(passport_obj, f_name, f_val)
        passport_obj.save()
        res_stat = status.HTTP_200_OK

    return schemas.PassportInfoModelSchema.from_orm(passport_obj), res_stat


@router.get('/{customer_id}/passport/',
            response_model=schemas.PassportInfoModelSchema
            )
def get_customer_passport(customer_id: int):
    passport_obj = get_object_or_404(models.PassportInfo, customer_id=customer_id)
    return schemas.PassportInfoModelSchema.from_orm(passport_obj)


@router.get('/service_type_report/',
            response_model=schemas.CustomerServiceTypeReportResponseSchema,
            dependencies=[Depends(permission_check_dependency(
                perm_codename='customers.can_view_service_type_report'
            ))]
            )
def service_type_report():
    r = models.Customer.objects.customer_service_type_report()
    return r


@router.get('/activity_report/',
            response_model=schemas.ActivityReportResponseSchema,
            dependencies=[Depends(permission_check_dependency(
                perm_codename='customers.can_view_activity_report'
            ))]
            )
def get_activity_report():
    r = models.Customer.objects.activity_report()
    return r


@router.get('/{customer_id}/is_access/', response_model=bool, responses={
    status.HTTP_200_OK: {'description': 'Shows is customer has access to any service'},
    status.HTTP_404_NOT_FOUND: {'description': 'Customer does not exists'}
})
def get_customer_is_access(customer_id: int):
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )
    return customer.is_access()


@router.get('/generate_password/', response_model=str)
def generate_password_for_customer():
    rp = serializers.generate_random_password()
    return rp


_mflags = tuple(f for f, n in models.Customer.MARKER_FLAGS)
@router.post('/{customer_id}/set_markers/', responses={
    status.HTTP_400_BAD_REQUEST: {'description': 'Bad flag names in body'},
    status.HTTP_204_NO_CONTENT: {'description': 'Markers applied successfully'}
})
def set_customer_markers(customer_id: int,
                         flag_names: list[str] = Body(title='Flag name list')):
    customer = get_object_or_404(
        models.Customer,
        pk=customer_id
    )
    for flag_name in flag_names:
        if flag_name not in _mflags:
            return Response(
                'Bad "flags". Must be an array of flag names. Such as %s' % _mflags,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    customer.set_markers(flag_names=flag_names)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/get_afk/', response_model=IListResponse[schemas.GetAfkResponseSchema])
def get_afk(date_limit: datetime,
            locality: int = 0,
            out_limit: int = 50):
    afk = models.Customer.objects.filter_afk(
        date_limit=date_limit,
        out_limit=out_limit
    )
    if locality > 0:
        addr_filtered_customers = models.Customer.objects.filter_customers_by_addr(
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


@router.get('/bums/',
            response_model_exclude={'password'},
            response_model=IListResponse[CustomerResponseModelSchema]
            )
@paginate_qs_path_decorator(schema=CustomerResponseModelSchema, db_model=models.Customer)
def get_customers_bums():
    qs = models.Customer.objects.filter(address=None)
    return qs


router.include_router(CrudRouter(
    schema=schemas.InvoiceForPaymentModelSchema,
    queryset=models.InvoiceForPayment.objects.select_related("customer", "author"),
), prefix='/invoices')

router.include_router(CrudRouter(
    schema=schemas.CustomerRawPasswordModelSchema,
    queryset=models.CustomerRawPassword.objects.select_related("customer"),
    create_route=False,
    get_all_route=False,
    delete_one_route=False
), prefix='/customer-raw-password')

router.include_router(CrudRouter(
    schema=schemas.AdditionalTelephoneModelSchema,
    create_schema=schemas.AdditionalTelephoneBaseSchema,
    queryset=models.AdditionalTelephone.objects.defer("customer"),
), prefix='/additional-telephone')

router.include_router(CrudRouter(
    schema=schemas.PeriodicPayForIdModelSchema,
    create_schema=schemas.PeriodicPayForIdBaseSchema,
    queryset=models.PeriodicPayForId.objects.defer("account").select_related("periodic_pay"),
), prefix='/periodic-pay')


@router.get('/attach_group_service/', response_model=list[schemas.AttachGroupServiceResponseSchema])
def attach_group_service_get(group: int):
    """Shows how services available in group"""

    grp = get_object_or_404(Group, pk=group)

    selected_services_id = tuple(pk[0] for pk in grp.service_set.only("pk").values_list("pk"))
    services = Service.objects.only("pk", "title").iterator()
    return (schemas.AttachGroupServiceResponseSchema(
        service=srv.pk,
        service_name=srv.title,
        check=srv.pk in selected_services_id
    ) for srv in services)


@router.post('/attach_group_service/', status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def attach_group_service(request_data: list[schemas.AttachGroupServiceResponseSchema], group: int):
    group = get_object_or_404(Group, pk=group)
    # selected_service_ids_db = frozenset(t.pk for t in group.service_set.only('pk'))
    all_available_service_ids_db = frozenset(srv.pk for srv in Service.objects.only("pk").iterator())

    # list of dicts: service<int>, check<bool>
    selected_service_ids = frozenset(
        s.service
        for s in request_data
        if s.check and s.service in all_available_service_ids_db
    )

    # add = selected_service_ids - selected_service_ids_db
    # sub = all_available_service_ids_db - (selected_service_ids - selected_service_ids_db)

    group.service_set.set(selected_service_ids)
    # models.Customer.objects.filter(
    #     group=group,
    #     last_connected_service__in=sub
    # ).update(last_connected_service=None)
    return


router.include_router(CrudRouter(
    schema=schemas.CustomerAttachmentModelSchema,
    create_schema=schemas.CustomerAttachmentBaseSchema,
    queryset=models.CustomerAttachment.objects.select_related("author"),
    create_route=False
), prefix='/attachments')


@router.post('/attachments/',
             response_model=schemas.CustomerAttachmentModelSchema,
             status_code=status.HTTP_201_CREATED)
def create_customer_attachment(
    attachment_data: schemas.CustomerAttachmentBaseSchema,
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
):
    user, token = auth
    pdict = attachment_data.dict()
    obj = models.CustomerAttachment.objects.create(**pdict, author_id=user.pk)
    return schemas.CustomerAttachmentModelSchema.from_orm(obj)


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
