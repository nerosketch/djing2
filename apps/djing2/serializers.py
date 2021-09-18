from bitfield import BitHandler
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


class BitFieldSerializer(serializers.Field):
    initial = []

    def to_representation(self, value):
        if isinstance(value, dict):
            return [i[0] for i in value.items() if i[1]]
        else:
            return int(value)

    def to_internal_value(self, data):
        model_field = getattr(self.root.Meta.model, self.source)
        result = BitHandler(0, model_field.keys())
        for k in data:
            try:
                setattr(result, str(k), True)
            except AttributeError:
                raise serializers.ValidationError("Unknown choice: %r" % (k,))
        return result
