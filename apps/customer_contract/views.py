from customer_contract import models
from customer_contract import serializers
from djing2.viewsets import DjingModelViewSet


class CustomerContractModelViewSet(DjingModelViewSet):
    queryset = models.CustomerContractModel.objects.all()
    serializer_class = serializers.CustomerContractModelSerializer
    filterset_fields = ('customer',)


class CustomerContractAttachmentModelViewSet(DjingModelViewSet):
    queryset = models.CustomerContractAttachmentModel.objects.all()
    serializer_class = serializers.CustomerContractAttachmentModelSerializer
    filterset_fields = ('contract',)
