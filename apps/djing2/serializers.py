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
        if isinstance(value, (int, float)):
            try:
                value = float(value)
            except ValueError:
                raise serializers.ValidationError('Must be number')
            # value must be in range "1/1/2000, 12:00:00 AM" < value < "1/1/2500, 12:00:00 AM"
            if 946677600 < value < 16725214800:
                converted = datetime.fromtimestamp(value)
                return converted
            else:
                raise serializers.ValidationError('Timestamp is exceeded range')
        return super().to_internal_value(value)
