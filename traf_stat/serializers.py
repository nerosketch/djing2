from rest_framework import serializers
from traf_stat.models import TrafficArchiveModel, TrafficCache


class TrafficArchiveModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficArchiveModel
        fields = '__all__'


class TrafficCacheModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficCache
        fields = '__all__'
