from django.db import transaction
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from customers import models, serializers
from customers.views.view_decorators import catch_customers_errs

from djing2.lib import LogicError, safe_int
from djing2.lib.mixins import SitesFilterMixin
from djing2.viewsets import BaseNonAdminReadOnlyModelViewSet
from services.models import Service


class SingleListObjMixin:
    def list(self, *args, **kwargs):
        del args, kwargs
        qs = self.get_queryset().first()
        sr = self.get_serializer(qs, many=False)
        return Response(sr.data)


class CustomersUserSideModelViewSet(SitesFilterMixin, SingleListObjMixin, BaseNonAdminReadOnlyModelViewSet):
    queryset = models.Customer.objects.select_related("group", "street", "gateway", "device", "current_service")
    serializer_class = serializers.CustomerModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(username=self.request.user.username)

    @action(methods=["post"], detail=False)
    @catch_customers_errs
    def buy_service(self, request):
        service_id = safe_int(request.data.get("service_id"))
        srv = get_object_or_404(Service, pk=service_id)
        customer = request.user

        customer.pick_service(
            service=srv,
            author=None,
            comment=_("Buy the service via user side, service '%s'") % srv,
            allow_negative=False,
        )
        # customer_gw_command.delay(
        #     customer_uid=customer.pk,
        #     command='sync'
        # )
        return Response(data=_("The service '%s' was successfully activated") % srv, status=status.HTTP_200_OK)

    @action(methods=("put",), detail=False)
    @catch_customers_errs
    def set_auto_new_service(self, request):
        auto_renewal_service = bool(request.data.get("auto_renewal_service"))
        customer = request.user
        customer.auto_renewal_service = auto_renewal_service
        customer.save(update_fields=["auto_renewal_service"])
        return Response()


class CustomerServiceModelViewSet(SingleListObjMixin, BaseNonAdminReadOnlyModelViewSet):
    queryset = models.CustomerService.objects.all()
    serializer_class = serializers.DetailedCustomerServiceModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer=self.request.user)


class LogsReadOnlyModelViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.CustomerLog.objects.all()
    serializer_class = serializers.CustomerLogModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer=self.request.user)


class DebtsList(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.InvoiceForPayment.objects.all()
    serializer_class = serializers.InvoiceForPaymentModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer=self.request.user)

    @action(methods=["post"], detail=True)
    @catch_customers_errs
    def buy(self, request, pk=None):
        del pk
        debt = self.get_object()
        customer = request.user
        sure = request.data.get("sure")
        if sure != "on":
            raise LogicError(_("Are you not sure that you want buy the service?"))
        if customer.balance < debt.cost:
            raise LogicError(_("Your account have not enough money"))

        with transaction.atomic():
            amount = -debt.cost
            customer.add_balance(
                profile=request.user,
                cost=amount,
                comment=gettext("%(username)s paid the debt %(amount).2f")
                % {"username": customer.get_full_name(), "amount": amount},
            )
            customer.save(update_fields=("balance",))
            debt.set_ok()
            debt.save(update_fields=("status", "date_pay"))
        return Response(status=status.HTTP_200_OK)
