from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from telebot import types

from djing2.viewsets import DjingModelViewSet
from messenger.models.telegram import TelegramMessenger


class TelegramMessengerModelViewSet(DjingModelViewSet):
    queryset = TelegramMessenger.objects.all()
    # serializer_class = serializers.TelegramMessengerSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'boturl'

    @action(detail=False)
    def send_webhook(self, request, pk=None):
        obj = self.get_object()
        obj.send_webhook()
        return Response(status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, permission_classes=[], url_name='listen_telegram_bot')
    def listen(self, request, pk=None):
        # obj = self.get_object()

        upd = types.Update.de_json(request.data)
        # Incoming updates from telegram bot
        if upd.message is not None:
            message

        return Response(status=status.HTTP_200_OK)
