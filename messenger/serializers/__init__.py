from djing2.lib.mixins import BaseCustomModelSerializer
from messenger import models


class MessengerModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.Messenger
        fields = '__all__'
