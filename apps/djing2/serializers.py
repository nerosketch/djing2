from datetime import datetime
from rest_framework import serializers


class SearchSerializer(serializers.Serializer):
    s = serializers.CharField(max_length=128, allow_blank=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class RequestObjectsPermsSerializer(serializers.Serializer):
    groupId = serializers.IntegerField(min_value=1)
    selectedPerms = serializers.ListField(child=serializers.IntegerField(min_value=1))

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class TimestampField(serializers.DateTimeField):
    """Convert a django datetime to/from timestamp"""

    def to_representation(self, value) -> float:
        """Convert the field to its internal representation (aka timestamp)
        :param value: the DateTime value
        :return: a UTC timestamp integer
        """
        result = super().to_representation(value)
        return result.timestamp()

    def to_internal_value(self, value):
        """
        deserialize a timestamp to a DateTime value
        :param value: the timestamp value
        :return: a django DateTime value
        """
        converted = datetime.fromtimestamp(float('%s' % value))
        return super().to_representation(converted)

