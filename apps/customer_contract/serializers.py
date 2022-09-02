from django.utils.translation import gettext_lazy as _
from djing2.lib.mixins import BaseCustomModelSerializer
from customer_contract import models


class CustomerContractModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerContractModel
        extra_kwargs = {
            'is_active': {'read_only': True},
            'title': {'initial': _('Contract default title')}
        }
        fields = '__all__'


class CustomerContractAttachmentModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerContractAttachmentModel
        fields = '__all__'
