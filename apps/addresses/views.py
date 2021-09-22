from djing2.viewsets import DjingModelViewSet
from addresses.models import AddressModel
from addresses.serializers import AddressModelSerializer
from djing2.lib.mixins import SitesFilterMixin


class AddressModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = AddressModel.objects.order_by('title')
    serializer_class = AddressModelSerializer
    filterset_fields = ['address_type']
