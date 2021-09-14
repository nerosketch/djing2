from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from djing2.viewsets import DjingModelViewSet, DjingAdminGenericAPIView
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

    # TODO: Protect this action.
    @action(methods=["post"], detail=True, permission_classes=[], url_name="listen-bot")
    def listen(self, request, pk=None):
        if not request.data:
            return Response('Empty data', status=status.HTTP_400_BAD_REQUEST)
        obj = self.get_queryset().filter(pk=pk).first()
        if obj is None:
            return Response('Messenger bot not found', status=status.HTTP_404_NOT_FOUND)
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


class NotificationProfileOptionsModelViewSet(DjingAdminGenericAPIView):
    queryset = models.NotificationProfileOptionsModel.objects.all()
    serializer_class = serializers.NotificationProfileOptionsModelSerializer

    def get_queryset(self):
        user = self.request.user
        return super().get_queryset().filter(profile=user)

    def get(self, request, format=None):
        obj = self.get_queryset().first()
        if obj is None:
            ser = self.serializer_class()
        else:
            ser = self.serializer_class(instance=obj)
            ser.is_valid(raise_exception=True)
        return Response(ser.data)

    def put(self, request, format=None):
        obj = self.get_queryset().first()
        if obj is None:
            ser = self.serializer_class(data=request.data)
            ser.is_valid(raise_exception=True)
            ser.save()
        else:
            ser = self.serializer_class(instance=obj, data=request.data)
            ser.is_valid(raise_exception=True)
            ser.save()
        return Response(ser.data)


@api_view(['get'])
def get_notification_options(request):
    res = {code: name for code, name in models.NotificationProfileOptionsModel.NOTIFICATION_FLAGS}
    return Response(res)
