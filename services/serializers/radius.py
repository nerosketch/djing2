from rest_framework import serializers


class RadiusServiceRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
