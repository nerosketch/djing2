from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app.models.base_payment_model import BasePaymentModel, BasePaymentLogModel


class BasePaymentModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = BasePaymentModel


class BasePaymentLogModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = BasePaymentLogModel
