from django.utils.translation import gettext_lazy as _, gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from customers import serializers
from customers import models
from customers.views.view_decorators import catch_customers_errs
from customers.tasks import customer_gw_command
from djing2.lib import safe_int, LogicError
from djing2.viewsets import BaseNonAdminReadOnlyModelViewSet, BaseNonAdminModelViewSet
from services.models import Service
from tasks.models import Task
from tasks.serializers import TaskModelSerializer


class SingleListObjMixin:
    def list(self, *args, **kwargs):
        qs = self.get_queryset().first()
        sr = self.get_serializer(qs, many=False)
        return Response(sr.data)


class CustomersUserSideModelViewSet(SingleListObjMixin, BaseNonAdminModelViewSet):
    queryset = models.Customer.objects.select_related(
        'group', 'street', 'gateway', 'device', 'current_service'
    ).only(
        'pk', 'username', 'telephone', 'fio',
        'group', 'group__title', 'balance', 'ip_address', 'description', 'street_id',
        'street__name',
        'house', 'is_active', 'gateway', 'gateway__title', 'auto_renewal_service',
        'device_id', 'device__comment', 'dev_port', 'last_connected_service_id', 'current_service_id',
        'is_dynamic_ip'
    )
    serializer_class = serializers.CustomerModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(username=self.request.user.username)

    @action(methods=('post',), detail=True)
    @catch_customers_errs
    def buy_service(self, request, pk=None):
        service_id = safe_int(request.data.get('service_id'))
        srv = get_object_or_404(Service, pk=service_id)
        customer = self.get_object()
        if customer != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        customer.pick_service(
            service=srv, author=None,
            comment=_("Buy the service via user side, service '%s'") % srv
        )
        customer_gw_command.delay(
            customer_uid=customer.pk,
            command='sync'
        )
        return Response(
            data=_("The service '%s' was successfully activated") % srv,
            status=status.HTTP_200_OK
        )


class CustomerServiceModelViewSet(SingleListObjMixin, BaseNonAdminModelViewSet):
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

    @action(methods=('post',), detail=True)
    @catch_customers_errs
    def buy(self, request, pk=None):
        debt = self.get_object()
        customer = self.request.user
        sure = request.data.get('sure')
        if sure != 'on':
            raise LogicError(
                _("Are you not sure that you want buy the service?")
            )
        if customer.balance < debt.cost:
            raise LogicError(_('Your account have not enough money'))

        amount = -debt.cost
        customer.add_balance(
            profile=self.request.user,
            cost=amount,
            comment=gettext('%(username)s paid the debt %(amount).2f') % {
                'username': customer.get_full_name(),
                'amount': amount
            }
        )
        customer.save(update_fields=('balance',))
        debt.set_ok()
        debt.save(update_fields=('status', 'date_pay'))
        return Response(status=status.HTTP_200_OK)


class TaskHistory(BaseNonAdminReadOnlyModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer=self.request.user)
