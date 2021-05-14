from djing2.viewsets import DjingModelViewSet
from messenger.models.messenger import Messenger
from messenger import serializers


class MessengerModelViewSet(DjingModelViewSet):
    queryset = Messenger.objects.all()
    serializer_class = serializers.MessengerModelSerializer
