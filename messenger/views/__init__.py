from djing2.viewsets import DjingModelViewSet
from messenger import models
from messenger import serializers


class MessengerModelViewSet(DjingModelViewSet):
    queryset = models.Messenger.objects.all()
    serializer_class = serializers.MessengerModelSerializer
