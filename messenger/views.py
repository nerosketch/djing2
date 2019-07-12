from djing2.viewsets import DjingModelViewSet
from messenger import models
from messenger import serializers


class MessengerModelViewSet(DjingModelViewSet):
    queryset = models.Messenger.objects.all()
    serializer_class = serializers.MessengerModelSerializer


class ViberMessengerModelViewSet(DjingModelViewSet):
    queryset = models.ViberMessenger.objects.all()
    serializer_class = serializers.ViberMessengerModelSerializer


class ViberMessageModelViewSet(DjingModelViewSet):
    queryset = models.ViberMessage.objects.all()
    serializer_class = serializers.ViberMessageModelSerializer


class ViberSubscriberModelViewSet(DjingModelViewSet):
    queryset = models.ViberSubscriber.objects.all()
    serializer_class = serializers.ViberSubscriberModelSerializer
