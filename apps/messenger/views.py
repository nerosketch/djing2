from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.exceptions import ParseError

from djing2.viewsets import DjingModelViewSet
from messenger.models import base_messenger as models
from messenger import serializers


class MessengerModelViewSet(DjingModelViewSet):
    queryset = models.MessengerModel.objects.all()
    serializer_class = serializers.MessengerModelSerializer

    @staticmethod
    def _get_specific_model(messenger_name: str):
        messenger_model = models.MessengerModel.class_map.get(messenger_name, None)
        if messenger_model is None:
            raise ParseError(detail='Unknown messenger name')
        return messenger_model

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

    @action(methods=["post"], detail=True, permission_classes=[], url_name="listen_bot",
            url_path=r'/(?P<messenger_name>\w{1,32})/listen')
    def listen(self, request, pk=None, messenger_name=None):
        specific_messenger_model = self._get_specific_model(messenger_name)
        obj = get_object_or_404(specific_messenger_model, pk=pk)
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
