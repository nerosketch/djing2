from typing import Optional

from customers import models
from django.utils.translation import gettext
from djing2.lib.fastapi.auth import is_customer_auth_dependency
from djing2.lib.fastapi.utils import get_object_or_404
from fastapi import APIRouter, Depends
from services.models import Service

from .view_decorators import catch_customers_errs
from .. import schemas

router = APIRouter(
    prefix='/customers/users',
    tags=['CustomersUserSide'],
    dependencies=[Depends(is_customer_auth_dependency)]
)

_base_customers_queryset = models.Customer.objects.select_related(
    "group", "gateway", "device", "current_service"
)


@router.get('/me/', response_model=schemas.UserCustomerModelSchema)
@catch_customers_errs
def get_me(current_user: models.Customer = Depends(is_customer_auth_dependency)):
    return schemas.UserCustomerModelSchema.from_orm(current_user)


@router.patch('/me/', response_model=schemas.UserCustomerModelSchema)
@catch_customers_errs
def update_me(data: schemas.UserCustomerWritableModelSchema,
              current_user: models.Customer = Depends(is_customer_auth_dependency)):
    for f_name, v_val in data.__fields__:
        setattr(current_user, f_name, v_val)
    current_user.save(update_fields=[f_name for f_name, _ in data.__fields__])
    return schemas.UserCustomerModelSchema.from_orm(current_user)


@router.post('/me/buy_service/', response_model=str)
@catch_customers_errs
def buy_service(payload: schemas.UserBuyServiceSchema,
                current_user: models.Customer = Depends(is_customer_auth_dependency)):
    service_id = payload.service_id
    srv = get_object_or_404(Service, pk=service_id)

    current_user.pick_service(
        service=srv,
        author=current_user,
        comment=gettext("Buy the service via user side, service '%s'") % srv,
        allow_negative=False,
    )
    # customer_gw_command.delay(
    #     customer_uid=customer.pk,
    #     command='sync'
    # )
    return gettext("The service '%s' was successfully activated") % srv


@router.put('/me/set_auto_new_service/')
@catch_customers_errs
def set_auto_new_service(payload: schemas.UserAutoRenewalServiceSchema,
                         current_user: models.Customer = Depends(is_customer_auth_dependency)):
    auto_renewal_service = bool(payload.auto_renewal_service)
    current_user.auto_renewal_service = auto_renewal_service
    current_user.save(update_fields=["auto_renewal_service"])
    return 'ok'


@router.get('/service/', response_model=Optional[schemas.DetailedCustomerServiceModelSchema])
def get_service_details(current_user: models.Customer = Depends(is_customer_auth_dependency)):
    act_srv = current_user.active_service()
    if act_srv:
        return schemas.DetailedCustomerServiceModelSchema.from_orm(act_srv)
    return None


@router.get('/log/',
            response_model=list[schemas.CustomerLogModelSchema],
            response_model_exclude=['author_name']
            )
def get_user_log(current_user: models.Customer = Depends(is_customer_auth_dependency)):
    qs = models.CustomerLog.objects.filter(customer=current_user)
    return (schemas.CustomerLogModelSchema.from_orm(log) for log in qs.iterator())


@router.get('/debts/',
            response_model=list[schemas.InvoiceForPaymentModelSchema],
            response_model_exclude=('author_name', 'author_uname')
            )
def get_user_debts(current_user: models.Customer = Depends(is_customer_auth_dependency)):
    qs = models.InvoiceForPayment.objects.filter(
        customer=current_user
    )
    return (schemas.CustomerLogModelSchema.from_orm(inv) for inv in qs.iterator())

# @action(methods=["post"], detail=True)
# @catch_customers_errs
# def buy(self, request, pk=None):
#    del pk
#    debt = self.get_object()
#    customer = request.user
#    sure = request.data.get("sure")
#    if sure != "on":
#        raise LogicError(_("Are you not sure that you want buy the service?"))
#    if customer.balance < debt.cost:
#        raise LogicError(_("Your account have not enough money"))

#    with transaction.atomic():
#        amount = -debt.cost
#        customer.add_balance(
#            profile=request.user,
#            cost=amount,
#            comment=gettext("%(username)s paid the debt %(amount).2f")
#            % {"username": customer.get_full_name(), "amount": amount},
#        )
#        customer.save(update_fields=("balance",))
#        debt.set_ok()
#        debt.save(update_fields=("status", "date_pay"))
#    return Response(status=status.HTTP_200_OK)
