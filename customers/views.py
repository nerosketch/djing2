from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
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


class SubscriberLogModelViewSet(DjingModelViewSet):
    queryset = models.SubscriberLog.objects.all()
    serializer_class = serializers.SubscriberLogModelSerializer


class SubscriberModelViewSet(DjingModelViewSet):
    queryset = models.Subscriber.objects.all()
    serializer_class = serializers.SubscriberModelSerializer


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


class GenerateRandomUsername(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request, format=None):
        username = serializers.generate_random_username()
        return Response(username)


class GenerateRandomPassword(GenerateRandomUsername):

    def get(self, request, format=None):
        passw = serializers.generate_random_password()
        return Response(passw)
