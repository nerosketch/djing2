from datetime import datetime
from django.utils.translation import gettext_lazy as _, gettext
from kombu.exceptions import OperationalError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from djing2.lib import safe_int, LogicError
from djing2.viewsets import DjingModelViewSet
from customers import models
from customers import serializers
from customers.tasks import customer_gw_command
from gateways.nas_managers import GatewayNetworkError, GatewayFailedResult
from services.models import Service


def catch_customers_errs(fn):
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except (GatewayFailedResult, GatewayNetworkError, OperationalError) as e:
            return Response(str(e), status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except LogicError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    # Hack for decorator @action
    wrapper.__name__ = fn.__name__
    return wrapper


class CustomerServiceModelViewSet(DjingModelViewSet):
    queryset = models.CustomerService.objects.all()
    serializer_class = serializers.CustomerServiceModelSerializer

    def create(self, request, *args, **kwargs):
        return Response(gettext(
            "Not allowed to direct create Customer service, use 'pick_service' url"
        ), status=status.HTTP_403_FORBIDDEN)


class CustomerStreetModelViewSet(DjingModelViewSet):
    queryset = models.CustomerStreet.objects.all()
    serializer_class = serializers.CustomerStreetModelSerializer
    filterset_fields = ('group',)


class CustomerLogModelViewSet(DjingModelViewSet):
    queryset = models.CustomerLog.objects.all()
    serializer_class = serializers.CustomerLogModelSerializer

    def create(self, request, *args, **kwargs):
        return Response(gettext(
            "Not allowed to direct create Customer log"
        ), status=status.HTTP_403_FORBIDDEN)


class CustomerModelViewSet(DjingModelViewSet):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerModelSerializer
    lookup_field = 'username'
    lookup_url_kwarg = 'uname'

    @staticmethod
    def generate_random_username(r):
        return Response(serializers.generate_random_username())

    @staticmethod
    def generate_random_password(r):
        return Response(serializers.generate_random_password())

    @action(methods=('post',), detail=True)
    @catch_customers_errs
    def pick_service(self, request, uname=None):
        service_id = safe_int(request.data.get('service_id'))
        deadline = request.data.get('deadline')
        srv = get_object_or_404(Service, pk=service_id)
        customer = self.get_object()
        log_comment = None
        if deadline:
            deadline = datetime.strptime(deadline, '%Y-%m-%dT%H:%M')
            log_comment = _(
                "Service '%(service_name)s' "
                "has connected via admin until %(deadline)s") % {
                              'service_name': srv.title,
                              'deadline': deadline
                          }
        customer.pick_service(
            service=srv,
            author=request.user,
            comment=log_comment,
            deadline=deadline
        )
        customer_gw_command.delay(customer.pk, 'sync')
        return Response(status=status.HTTP_200_OK)


class PassportInfoModelViewSet(DjingModelViewSet):
    queryset = models.PassportInfo.objects.all()
    serializer_class = serializers.PassportInfoModelSerializer


class InvoiceForPaymentModelViewSet(DjingModelViewSet):
    queryset = models.InvoiceForPayment.objects.all()
    serializer_class = serializers.InvoiceForPaymentModelSerializer


class CustomerRawPasswordModelViewSet(DjingModelViewSet):
    queryset = models.CustomerRawPassword.objects.all()
    serializer_class = serializers.CustomerRawPasswordModelSerializer


class AdditionalTelephoneModelViewSet(DjingModelViewSet):
    queryset = models.AdditionalTelephone.objects.all()
    serializer_class = serializers.AdditionalTelephoneModelSerializer


class PeriodicPayForIdModelViewSet(DjingModelViewSet):
    queryset = models.PeriodicPayForId.objects.all()
    serializer_class = serializers.PeriodicPayForIdModelSerializer
