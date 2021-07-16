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
        uint, messenger_model_class = models.class_map.get(messenger_name, None)
        if messenger_model_class is None:
            raise ParseError(detail='Unknown messenger name')
        return messenger_model_class

    @action(detail=True)
    def send_webhook(self, request, pk=None):
        """
        Sends webhook url to messenger server.
        """
        # TODO: May optimize it?
        obj = self.get_object()
        spec_model = models.get_messenger_model_by_uint(int(obj.bot_type))
        spec_obj = get_object_or_404(spec_model, pk=pk)
        spec_obj.send_webhook(request)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def stop_webhook(self, request, pk=None):
        """
        Stop sending webhook.
        """
        # TODO: May optimize it?
        obj = self.get_object()
        spec_model = models.get_messenger_model_by_uint(int(obj.bot_type))
        spec_obj = get_object_or_404(spec_model, pk=pk)
        spec_obj.stop_webhook(request)
        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, permission_classes=[], url_name="listen-bot",
            url_path=r'(?P<messenger_name>\w{1,32})/listen')
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

    @action(methods=['get'], detail=False)
    def get_bot_types(self, request):
        g = ((int_and_class[0], type_name) for type_name, int_and_class in models.class_map.items())
        return Response(g)


class SubscriberModelViewSet(DjingModelViewSet):
    queryset = models.MessengerSubscriberModel.objects.all()
    serializer_class = serializers.MessengerSubscriberModelSerializer
