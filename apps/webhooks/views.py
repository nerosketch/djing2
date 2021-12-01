from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from webhooks.models import HookObserver
from webhooks.serializers import HookObserverModelSerializer, ContentTypeModelSerializer


class HookObserverModelViewSet(ModelViewSet):
    queryset = HookObserver.objects.all()
    serializer_class = HookObserverModelSerializer

    @action(methods=['put'], detail=False)
    def subscribe(self, request):
        return self.create(request)

    @action(methods=['put'], detail=False)
    def unsubscribe(self, request):
        serializer = self.get_serializer(data=request.data)
        # serializer.is_valid(raise_exception=False)
        obj_qs = self.queryset.filter(
            **serializer.data
        )
        if obj_qs.exists():
            obj_qs.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response('Subscription not found', status=status.HTTP_404_NOT_FOUND)


class ContentTypeModelViewSet(ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeModelSerializer
