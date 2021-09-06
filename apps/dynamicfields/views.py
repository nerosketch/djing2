from abc import abstractmethod, ABC
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from dynamicfields.models import FieldModel
from dynamicfields.serializers import FieldModelSerializer
from djing2.viewsets import DjingModelViewSet


class FieldModelViewSet(DjingModelViewSet):
    queryset = FieldModel.objects.all()
    serializer_class = FieldModelSerializer


class AbstractDynamicFieldContentModelViewSet(ABC, DjingModelViewSet):
    def get_serializer_class(self):
        class TemporaryDynamicFieldContentModelSerializer(serializers.ModelSerializer):
            class Meta:
                model = self.get_queryset().model
                fields = '__all__'

        return TemporaryDynamicFieldContentModelSerializer

    @abstractmethod
    def get_group_id(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def filter_content_fields_queryset(self):
        raise NotImplementedError

    def create_content_field_kwargs(self):
        return {}

    @action(methods=['get'], detail=False)
    def combine(self, request):
        group_id = self.get_group_id()

        field_models = FieldModel.objects.filter(
            groups__in=[group_id]
        ).values()

        field_content_models = self.filter_content_fields_queryset().filter(
            field__groups__in=[group_id]
        ).values()
        field_content_models_map = {fcm['field_id']: fcm for fcm in field_content_models}

        res = []
        for fm in field_models:
            serializer_class = self.get_serializer_class()
            ser = serializer_class(data={
                'field': fm.get('id')
            })
            ser.is_valid()
            content_field_data = ser.data

            content_field = field_content_models_map.get(fm.get('id'))
            if content_field is not None:
                content_field_data.update({
                    'id': content_field.get('id'),
                    'content': content_field.get('content'),
                })

            res.append(content_field_data)

        return Response(res)

    @action(methods=['put'], detail=False)
    def update_all(self, request):
        data = request.data
        content_field_model = self.get_queryset().model
        for field_data in data:
            content = field_data.get('content')
            field = field_data.get('field')
            # customer = field_data.get('customer')
            pk = safe_int(field_data.get('id'))
            if pk > 0:
                content_field_model.objects.filter(pk=pk).update(content=content)
            else:
                create_kwargs = self.create_content_field_kwargs()
                content_field_model.objects.create(
                    content=content,
                    field_id=field,
                    *create_kwargs
                )

        return Response('ok')
