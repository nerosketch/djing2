from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from customers import serializers
from customers import models
from customers.views.view_decorators import catch_customers_errs
from customers.tasks import customer_gw_command
from djing2.lib import safe_int
from djing2.viewsets import BaseNonAdminReadOnlyModelViewSet
from services.models import Service


class CustomersReadOnlyModelViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.Customer.objects.all()
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
            data=_("The service '%s' wan successfully activated") % srv,
            status=status.HTTP_200_OK
        )


class LogsReadOnlyModelViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.CustomerLog.objects.all()
    serializer_class = serializers.CustomerLogModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer=self.request.user)

