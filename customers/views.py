from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from customers import models
from customers import serializers


class CustomerServiceModelViewSet(DjingModelViewSet):
    queryset = models.CustomerService.objects.all()
    serializer_class = serializers.CustomerServiceModelSerializer


class CustomerStreetModelViewSet(DjingModelViewSet):
    queryset = models.CustomerStreet.objects.all()
    serializer_class = serializers.CustomerStreetModelSerializer
    filterset_fields = ('group',)


class CustomerLogModelViewSet(DjingModelViewSet):
    queryset = models.CustomerLog.objects.all()
    serializer_class = serializers.CustomerLogModelSerializer


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
