#  from django.db.models import Count
from djing2.viewsets import DjingModelViewSet
from rest_framework.exceptions import ValidationError
from fin_app.models.base_payment_model import (
    BasePaymentModel,
    BasePaymentLogModel
)
from fin_app.serializers.base import (
    BasePaymentModelSerializer,
    BasePaymentLogModelSerializer
)


class BasePaymentGatewayModelViewSet(DjingModelViewSet):
    #  queryset = BasePaymentModel.objects.annotate(pay_count=Count("alltimepaymentlog"))
    queryset = BasePaymentModel.objects.order_by('id')
    serializer_class = BasePaymentModelSerializer

    def perform_create(self, serializer, *args, **kwargs):
        raise ValidationError("Base payment model can't direct creation")


class BasePaymentLogModelViewSet(DjingModelViewSet):
    queryset = BasePaymentLogModel.objects.all()
    serializer_class = BasePaymentLogModelSerializer

    def perform_create(self, serializer, *args, **kwargs):
        raise ValidationError("Base payment log can't direct creation")
