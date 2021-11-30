from rest_framework.viewsets import ModelViewSet
from webhooks.models import HookObserver
from webhooks.serializers import HookObserverModelSerializer


class HookObserverModelViewSet(ModelViewSet):
    queryset = HookObserver.objects.all()
    serializer_class = HookObserverModelSerializer
