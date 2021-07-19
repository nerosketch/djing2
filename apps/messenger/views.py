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
        spec_obj.send_webhook()
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
        spec_obj.stop_webhook()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def show_webhook(self, request, pk=None):
        """ Show current webhook url."""
        # TODO: May optimize it?
        obj = self.get_object()
        spec_model = models.get_messenger_model_by_uint(int(obj.bot_type))
        spec_obj = get_object_or_404(spec_model, messengermodel_ptr_id=pk)
        type_name = obj.get_type_name()
        webhook_url = spec_obj.get_webhook_url(type_name=type_name)
        return Response(webhook_url)

    @action(methods=["post"], detail=True, permission_classes=[], url_name="listen-bot",
            url_path=r'(?P<messenger_name>\w{1,32})/listen')
    def listen(self, request, pk=None, messenger_name=None):
        specific_messenger_model = self._get_specific_model(messenger_name)
        obj = get_object_or_404(specific_messenger_model, pk=pk)
        r = obj.inbox_data(request)
        if isinstance(r, (tuple, list)):
            ret_text, ret_code = r
            return Response(ret_text, status=ret_code)
        elif isinstance(r, (str, dict, list)) or hasattr(r, "__str__"):
            return Response(r)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def get_bot_types(self, request):
        g = ((int_and_class[0], type_name) for type_name, int_and_class in models.class_map.items())
        return Response(g)

    @action(methods=['post'], detail=False)
    def create_inherited(self, request):
        dat = request.data
        bot_type = dat.pop('bot_type')
        if not bot_type:
            return Response('bad "bot_type"', status=status.HTTP_400_BAD_REQUEST)
        new_inst = models.MessengerModel.objects.create_inherited(bot_type=bot_type, **dat)
        serializer = self.get_serializer(new_inst)
        return Response(serializer.data)


class SubscriberModelViewSet(DjingModelViewSet):
    queryset = models.MessengerSubscriberModel.objects.all()
    serializer_class = serializers.MessengerSubscriberModelSerializer
