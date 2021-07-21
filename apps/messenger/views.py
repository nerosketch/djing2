from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from messenger.models import base_messenger as models
from messenger import serializers


class MessengerModelViewSet(DjingModelViewSet):
    serializer_class = serializers.MessengerModelSerializer

    @action(detail=True)
    def send_webhook(self, request, pk=None):
        """
        Sends webhook url to messenger server.
        """
        obj = self.get_object()
        obj.send_webhook()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def stop_webhook(self, request, pk=None):
        """
        Stop sending webhook.
        """
        obj = self.get_object()
        obj.stop_webhook()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def show_webhook(self, request, pk=None):
        """ Show current webhook url."""
        obj = self.get_object()
        webhook_url = obj.get_webhook_url()
        return Response(webhook_url)

    @action(methods=["post"], detail=True, permission_classes=[], url_name="listen-bot")
    def listen(self, request, pk=None):
        obj = self.get_object()
        r = obj.inbox_data(request)
        if isinstance(r, (tuple, list)):
            ret_text, ret_code = r
            return Response(ret_text, status=ret_code)
        elif isinstance(r, (str, dict, list)) or hasattr(r, "__str__"):
            return Response(r)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['get'])
def get_bot_types(request):
    g = ((int_and_class[0], type_name) for type_name, int_and_class in models.class_map.items())
    return Response(g)


class SubscriberModelViewSet(DjingModelViewSet):
    queryset = models.MessengerSubscriberModel.objects.all()
    serializer_class = serializers.MessengerSubscriberModelSerializer
