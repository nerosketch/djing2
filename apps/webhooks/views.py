from django.contrib.contenttypes.models import ContentType
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from webhooks.models import HookObserver
from webhooks.serializers import HookObserverModelSerializer, ContentTypeModelSerializer


class HookObserverModelViewSet(ModelViewSet):
    queryset = HookObserver.objects.all()
    serializer_class = HookObserverModelSerializer


class ContentTypeModelViewSet(ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeModelSerializer
