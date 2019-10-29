from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from customers.models import Customer
from networks.serializers import NetworkModelSerializer
from networks.models import NetworkModel


class NetworkModelViewSet(DjingModelViewSet):
    queryset = NetworkModel.objects.all()
    serializer_class = NetworkModelSerializer
    filter_backends = (OrderingFilter,)
    ordering_fields = ('network', 'kind', 'description', 'cost', 'usercount')

    @action(detail=True, methods=('post',))
    def group_attach(self, request, pk=None):
        network = self.get_object()
        gr = request.POST.getlist('gr')
        network.groups.clear()
        network.groups.add(*gr)
        return Response(status=status.HTTP_200_OK)

    # @action(detail=True)
    # def selected_groups(self, request, pk=None):
    #     net = self.get_object()
    #     selected_grps = (pk[0] for pk in net.groups.only('pk').values_list('pk'))
    #     return Response(selected_grps)

    @action(detail=True)
    def get_free_ip(self, request, pk=None):
        network = self.get_object()
        q = Customer.objects.exclude(ip_address=None).exclude(gateway=None).iterator()
        used_ips = (c.ip_address for c in q)
        ip = network.get_free_ip(employed_ips=used_ips)
        if ip is None:
            return Response()
        return Response(str(ip))
