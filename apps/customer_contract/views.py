from customer_contract import models
from customer_contract import serializers
from djing2.viewsets import DjingModelViewSet


class CustomerContractModelViewSet(DjingModelViewSet):
    queryset = models.CustomerContractModel.objects.all()
    serialzier_class = serializers.CustomerContractModelSerializer


class CustomerContractAttachmentModelViewSet(DjingModelViewSet):
    queryset = models.CustomerContractAttachmentModel.objects.all()
    serialzier_class = serializers.CustomerContractAttachmentModelSerializer
