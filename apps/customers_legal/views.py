from rest_framework.generics import get_object_or_404

from customers_legal.models import CustomerLegalModel, CustomerLegalDynamicFieldContentModel
from customers_legal.serializers import CustomerLegalModelSerializer
from djing2.viewsets import DjingModelViewSet
from dynamicfields.views import AbstractDynamicFieldContentModelViewSet


class CustomerLegalDynamicFieldContentModelViewSet(AbstractDynamicFieldContentModelViewSet):
    queryset = CustomerLegalDynamicFieldContentModel.objects.all()

    def get_group_id(self) -> int:
        legal_customer_id = self.request.query_params.get('legal_customer_id')
        self.legal_customer_id = legal_customer_id
        legal_customer = get_object_or_404(CustomerLegalModel.objects.only('group_id'), pk=legal_customer_id)
        self.legal_customer = legal_customer
        return legal_customer.group_id

    def filter_content_fields_queryset(self):
        return self.get_queryset().objects.filter(
            legal_customer_id=self.legal_customer_id
        )

    def create_content_field_kwargs(self, field_data):
        if hasattr(self, 'legal_id'):
            return {
                'legal_customer_id': self.legal_customer_id
            }
        return {
            'legal_customer_id': field_data.get('legal_customer')
        }


class CustomerLegalModelViewSet(DjingModelViewSet):
    queryset = CustomerLegalModel.objects.all()
    serializer_class = CustomerLegalModelSerializer
