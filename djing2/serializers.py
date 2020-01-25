from rest_framework import serializers


class SearchSerializer(serializers.Serializer):
    s = serializers.CharField(max_length=128, allow_blank=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
