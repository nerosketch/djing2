from rest_framework import serializers


class DrawflowInputSerializer(serializers.Serializer):
    pass


class DrawflowOuputSerializer(serializers.Serializer):
    pass


class DrawflowFormatSerializer(serializers.Serializer):
    klass = serializers.CharField(name='class')
    data = serializers.DictField()
    html = serializers.CharField()
    id = serializers.IntegerField()
    name = serializers.CharField()
    inputs = DrawflowInputSerializer(many=True)
    outputs = DrawflowOuputSerializer(many=True)
    pos_x = serializers.FloatField(default=0)
    pos_y = serializers.FloatField(default=0)
    typenode = serializers.CharField()
