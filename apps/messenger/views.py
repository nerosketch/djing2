from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from messenger.models import messenger as models
from messenger import serializers


class MessengerModelViewSet(DjingModelViewSet):
    queryset = models.MessengerModel.objects.all()
    serializer_class = serializers.MessengerModelSerializer

    @action(detail=True)
    def send_webhook(self, request, pk=None):
        obj = self.get_object()
        obj.send_webhook(request)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def stop_webhook(self, request, pk=None):
        obj = self.get_object()
        obj.stop_webhook(request)
        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, permission_classes=[], url_name="listen_bot")
    def listen(self, request, pk=None):
        obj = self.get_object()
        r = obj.inbox_data(request)
        if isinstance(r, (tuple, list)):
            ret_text, ret_code = r
            return Response(ret_text, status=ret_code)
        elif isinstance(r, str) or hasattr(r, "__str__"):
            return Response(r, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubscriberModelViewSet(DjingModelViewSet):
    queryset = models.MessengerSubscriberModel.objects.all()
    serializer_class = serializers.MessengerSubscriberModelSerializer
