from djing2.lib.mixins import BaseCustomModelSerializer
from traf_stat.models import TrafficArchiveModel, TrafficCache


class TrafficArchiveModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = TrafficArchiveModel
        fields = '__all__'


class TrafficCacheModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = TrafficCache
        fields = '__all__'
