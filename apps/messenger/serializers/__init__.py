from djing2.lib.mixins import BaseCustomModelSerializer
from messenger.models.messenger import Messenger


class MessengerModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Messenger
        fields = "__all__"
