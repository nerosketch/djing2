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

    def to_internal_value(self, value: float) -> datetime:
        """
        deserialize a timestamp to a DateTime value
        :param value: the timestamp value
        :return: a django DateTime value
        """
        if not isinstance(value, (int, float, str)):
            raise serializers.ValidationError('Must be int')
        value = float(value)
        converted = datetime.fromtimestamp(value)
        return converted
