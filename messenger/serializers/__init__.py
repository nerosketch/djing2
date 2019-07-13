from rest_framework import serializers
from messenger import models


class MessengerModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Messenger
        fields = '__all__'
