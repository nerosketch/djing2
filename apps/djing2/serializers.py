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
