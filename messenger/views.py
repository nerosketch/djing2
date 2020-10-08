from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from messenger import models
from messenger import serializers


class MessengerModelViewSet(DjingModelViewSet):
    queryset = models.Messenger.objects.all()
    serializer_class = serializers.MessengerModelSerializer

    @action(detail=True)
    def send_webhook(self, request, pk=None):
        obj = self.get_object()
        obj.send_webhook()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def stop_webhook(self, request, pk=None):
        obj = self.get_object()
        obj.remove_webhook()
        return Response(status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, permission_classes=[], url_name='listen_telegram_bot')
    def listen(self, request, pk=None):
        obj = self.get_object()
        r = obj.inbox_data(request.data)
        return Response(r, status=status.HTTP_200_OK)


class MessageModelViewSet(DjingModelViewSet):
    queryset = models.MessengerMessage.objects.all()
    serializer_class = serializers.MessengerMessageModelSerializer


class SubscriberModelViewSet(DjingModelViewSet):
    queryset = models.MessengerSubscriber.objects.all()
    serializer_class = serializers.MessengerSubscriberModelSerializer
