from customer_contract import models
from customer_contract import serializers
from djing2.viewsets import DjingModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response


class CustomerContractModelViewSet(DjingModelViewSet):
    queryset = models.CustomerContractModel.objects.all()
    serializer_class = serializers.CustomerContractModelSerializer
    filterset_fields = ('customer',)

    @action(methods=['put'], detail=True)
    def finish(self, request, pk=None):
        contract = self.get_object()
        contract.finish()
        return Response('ok')


class CustomerContractAttachmentModelViewSet(DjingModelViewSet):
    queryset = models.CustomerContractAttachmentModel.objects.all()
    serializer_class = serializers.CustomerContractAttachmentModelSerializer
    filterset_fields = ('contract',)
