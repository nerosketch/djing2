from typing import Optional
from django.contrib.contenttypes.models import ContentType
from starlette import status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from webhooks.models import HookObserver
from webhooks.serializers import (
    HookObserverModelSerializer,
    ContentTypeModelSerializer,
    HookObserverSubscribeSerializer
)


class HookObserverModelViewSet(ModelViewSet):
    queryset = HookObserver.objects.all()
    serializer_class = HookObserverModelSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)

    def find_hook_observer_model(self, request_data) -> Optional[dict]:
        ser = HookObserverSubscribeSerializer(data=request_data)
        ser.is_valid(raise_exception=True)
        data = ser.data
        data_ct = data.get('content_type')
        if not data_ct:
            return None
        ct = get_object_or_404(ContentType,
            app_label=data_ct.get('app_label'),
            model=data_ct.get('model')
        )
        find_kwargs = {
            'notification_type': data.get('notification_type'),
            'client_url': data.get('client_url'),
            'content_type': ct
        }
        return find_kwargs

    @action(methods=['put'], detail=False)
    def subscribe(self, request):
        find_kwargs = self.find_hook_observer_model(request.data)
        if not find_kwargs:
            return Response('Hook observer model not found', status=status.HTTP_404_NOT_FOUND)
        ho, created = HookObserver.objects.get_or_create(**find_kwargs, defaults={
            'user': request.user
        })

        serializer = self.serializer_class(instance=ho)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            headers=headers
        )

    @subscribe.mapping.get
    def subscribe_get(self, request):
        ser = HookObserverSubscribeSerializer()
        return Response(ser.data)

    @action(methods=['put'], detail=False)
    def unsubscribe(self, request):
        find_kwargs = self.find_hook_observer_model(request.data)
        if not find_kwargs:
            return Response('Hook observer model not found', status=status.HTTP_404_NOT_FOUND)
        ho = HookObserver.objects.filter(**find_kwargs)
        if not ho.exists():
            return Response('hook not found', status=status.HTTP_404_NOT_FOUND)
        ho.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContentTypeModelViewSet(ReadOnlyModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeModelSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
