from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from customers_legal import models
from customers_legal import serializers
from djing2.viewsets import DjingModelViewSet
from dynamicfields.views import AbstractDynamicFieldContentModelViewSet


class CustomerLegalDynamicFieldContentModelViewSet(AbstractDynamicFieldContentModelViewSet):
    queryset = models.CustomerLegalDynamicFieldContentModel.objects.all()

    def get_group_id(self) -> int:
        legal_customer_id = self.request.query_params.get('legal_customer_id')
        self.legal_customer_id = legal_customer_id
        legal_customer = get_object_or_404(models.CustomerLegalModel.objects.only('group_id'), pk=legal_customer_id)
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
    queryset = models.CustomerLegalModel.objects.all()
    serializer_class = serializers.CustomerLegalModelSerializer

    @action(methods=['get'], detail=False)
    def get_legal_types(self, request):
        res = ({'value': k, 'label': v} for k, v in models.CustomerLegalIntegerChoices.choices)
        return Response(res)


class LegalCustomerBankModelViewSet(DjingModelViewSet):
    queryset = models.LegalCustomerBankModel.objects.all()
    serializer_class = serializers.LegalCustomerBankModelSerializer
    filterset_fields = ('legal_customer',)


class CustomerLegalTelephoneModelViewSet(DjingModelViewSet):
    queryset = models.CustomerLegalTelephoneModel.objects.all()
    serializer_class = serializers.CustomerLegalTelephoneModelSerializer

