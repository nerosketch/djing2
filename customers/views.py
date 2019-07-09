from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from customers import models
from customers import serializers


class SubscriberServiceModelViewSet(DjingModelViewSet):
    queryset = models.SubscriberService.objects.all()
    serializer_class = serializers.SubscriberServiceModelSerializer


class SubscriberStreetModelViewSet(DjingModelViewSet):
    queryset = models.SubscriberStreet.objects.all()
    serializer_class = serializers.SubscriberStreetModelSerializer
    filterset_fields = ('group',)


class SubscriberLogModelViewSet(DjingModelViewSet):
    queryset = models.SubscriberLog.objects.all()
    serializer_class = serializers.SubscriberLogModelSerializer


class SubscriberModelViewSet(DjingModelViewSet):
    queryset = models.Subscriber.objects.all()
    serializer_class = serializers.SubscriberModelSerializer
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


class SubscriberRawPasswordModelViewSet(DjingModelViewSet):
    queryset = models.SubscriberRawPassword.objects.all()
    serializer_class = serializers.SubscriberRawPasswordModelSerializer


class AdditionalTelephoneModelViewSet(DjingModelViewSet):
    queryset = models.AdditionalTelephone.objects.all()
    serializer_class = serializers.AdditionalTelephoneModelSerializer


class PeriodicPayForIdModelViewSet(DjingModelViewSet):
    queryset = models.PeriodicPayForId.objects.all()
    serializer_class = serializers.PeriodicPayForIdModelSerializer
