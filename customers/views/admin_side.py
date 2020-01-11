from datetime import datetime

from django.conf import settings
from django.db.models import Count
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _, gettext
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import get_objects_for_user
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from agent.commands.dhcp import dhcp_commit, dhcp_expiry, dhcp_release
from customers import models
from customers import serializers
from customers.tasks import customer_gw_command, customer_gw_remove
from customers.views.view_decorators import catch_customers_errs
from djing2.lib import safe_int, LogicError, DuplicateEntry, safe_float
from djing2.lib.mixins import SecureApiView
from djing2.lib.paginator import QueryPageNumberPagination
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from gateways.models import Gateway
from gateways.nas_managers import GatewayNetworkError, GatewayFailedResult
from groupapp.models import Group
from services.models import Service, OneShotPay
from services.serializers import ServiceModelSerializer


class CustomerServiceModelViewSet(DjingModelViewSet):
    queryset = models.CustomerService.objects.all()
    serializer_class = serializers.CustomerServiceModelSerializer

    def create(self, request, *args, **kwargs):
        return Response(gettext(
            "Not allowed to direct create Customer service, use 'pick_service' url"
        ), status=status.HTTP_403_FORBIDDEN)


class CustomerStreetModelViewSet(DjingModelViewSet):
    queryset = models.CustomerStreet.objects.select_related(
        'group'
    )
    serializer_class = serializers.CustomerStreetModelSerializer
    filterset_fields = ('group',)


class CustomerLogModelViewSet(DjingModelViewSet):
    queryset = models.CustomerLog.objects.select_related(
        'customer', 'author'
    )
    serializer_class = serializers.CustomerLogModelSerializer
    filterset_fields = ('customer', )

    def create(self, request, *args, **kwargs):
        return Response(gettext(
            "Not allowed to direct create Customer log"
        ), status=status.HTTP_403_FORBIDDEN)


class CustomerModelViewSet(DjingModelViewSet):
    queryset = models.Customer.objects.select_related(
        'group', 'street', 'gateway', 'device', 'dev_port',
        'current_service', 'last_connected_service',
        'current_service__service', 'customerrawpassword'
    )
    serializer_class = serializers.CustomerModelSerializer
    filter_backends = (SearchFilter, DjangoFilterBackend, OrderingFilter)
    search_fields = ('username', 'fio', 'telephone', 'description')
    filterset_fields = ('group', 'street', 'device', 'dev_port')
    ordering_fields = ('username', 'fio', 'house', 'balance')

    @staticmethod
    def generate_random_username(_):
        return Response(serializers.generate_random_username())

    @staticmethod
    def generate_random_password(_):
        return Response(serializers.generate_random_password())

    @action(methods=('post',), detail=True)
    @catch_customers_errs
    def pick_service(self, request, pk=None):
        del pk
        service_id = safe_int(request.data.get('service_id'))
        deadline = request.data.get('deadline')
        srv = get_object_or_404(Service, pk=service_id)
        customer = self.get_object()
        log_comment = None
        if deadline:
            deadline = datetime.strptime(deadline, '%Y-%m-%dT%H:%M')
            log_comment = _(
                "Service '%(service_name)s' "
                "has connected via admin until %(deadline)s") % {
                              'service_name': srv.title,
                              'deadline': deadline
                          }
        try:
            customer.pick_service(
                service=srv,
                author=request.user,
                comment=log_comment,
                deadline=deadline,
                allow_negative=True
            )
            customer_gw_command.delay(customer.pk, 'sync')
        except models.NotEnoughMoney as e:
            return Response(data=str(e), status=status.HTTP_402_PAYMENT_REQUIRED)
        return Response(status=status.HTTP_200_OK)

    @action(methods=('post',), detail=True)
    @catch_customers_errs
    def make_shot(self, request, pk=None):
        customer = self.get_object()
        shot_id = safe_int(request.data.get('shot_id'))
        shot = get_object_or_404(OneShotPay, pk=shot_id)
        shot.before_pay(request=request, customer=customer)
        r = customer.make_shot(request, shot, allow_negative=True)
        shot.after_pay(request=request, customer=customer)
        if not r:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(r)

    @action(methods=('get',), detail=False)
    @catch_customers_errs
    def service_users(self, request):
        service_id = safe_int(request.query_params.get('service_id'))
        if service_id == 0:
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = models.Customer.objects.filter(
            current_service__service__id=service_id
        ).select_related('group').values(
            'id', 'group_id', 'username', 'fio'
        )
        return Response(qs)

    @action(detail=True)
    @catch_customers_errs
    def stop_service(self, request, pk=None):
        del pk
        customer = self.get_object()
        cust_srv = customer.active_service()
        if cust_srv is None:
            return Response(data=_('Service not connected'))

        srv = cust_srv.service
        if srv is None:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if customer.gateway:
            customer_gw_remove.delay(
                customer_uid=int(customer.pk),
                ip_addr=str(customer.ip_address),
                speed=(srv.speed_in, srv.speed_out),
                is_access=customer.is_access(),
                gw_pk=int(customer.gateway_id)
            )
        customer.stop_service(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=('post',), detail=False)
    @catch_customers_errs
    def attach_nas(self, request):
        gateway_id = request.data.get('gateway')
        if not gateway_id:
            return Response(_('You must specify gateway'), status=status.HTTP_400_BAD_REQUEST)
        gateway_id = safe_int(gateway_id)
        gid = request.data.get('group')
        if not gid:
            return Response(_('You must specify group'), status=status.HTTP_400_BAD_REQUEST)
        gid = safe_int(gid)
        gw = get_object_or_404(Gateway, pk=gateway_id)
        customers = models.Customer.objects.filter(group__id=gid)
        if customers.exists():
            customers.update(gateway=gw)
            return Response(
                _('Network access server for users in this '
                  'group, has been updated'),
                status=status.HTTP_200_OK
            )
        else:
            return Response(_('Users not found'))

    @action(detail=True)
    @catch_customers_errs
    def ping(self, request, pk=None):
        del request, pk
        customer = self.get_object()
        ip = customer.ip_address
        if ip is None:
            raise LogicError(_('Ip not passed'))
        if customer.gateway is None:
            raise LogicError(_('gateway required'))
        mngr = customer.gateway.get_gw_manager()
        try:
            ping_result = mngr.ping(ip)
        except (GatewayNetworkError, GatewayFailedResult) as e:
            return Response({
                'text': str(e),
                'status': False
            })
        no_ping_response = Response({
            'text': _('no ping'),
            'status': False
        })
        r_status = True
        if ping_result is None:
            return no_ping_response
        if isinstance(ping_result, tuple):
            received, sent = ping_result
            if received == 0:
                ping_result = mngr.ping(ip, arp=True)
                if ping_result is not None and isinstance(ping_result, tuple):
                    received, sent = ping_result
                else:
                    return no_ping_response
            loses_percent = (
                received / sent if sent != 0 else 1
            )
            ping_result = {'return': received, 'all': sent}
            if loses_percent > 1.0:
                text = 'IP Conflict! %(return)d/%(all)d results'
                r_status = False
            elif loses_percent > 0.5:
                text = 'ok ping, %(return)d/%(all)d loses'
            else:
                text = 'no ping, %(return)d/%(all)d loses'
                r_status = False
            text = gettext(text) % ping_result
            return Response({
                'text': text,
                'status': r_status
            })
        return no_ping_response

    @action(detail=True)
    @catch_customers_errs
    def current_service(self, request, pk=None):
        del request, pk
        customer = self.get_object()
        if not customer.current_service:
            return Response(False)
        curr_srv = customer.current_service
        ser = ServiceModelSerializer(instance=curr_srv.service)
        r = {
            'start_time': curr_srv.start_time,
            'deadline': curr_srv.deadline,
            'service': ser.data
        }
        if customer.last_connected_service:
            r['last_connected_service'] = customer.last_connected_service.title
        return Response(r)

    @action(methods=('post',), detail=True)
    @catch_customers_errs
    def add_balance(self, request, pk=None):
        del pk
        customer = self.get_object()

        cost = safe_float(request.data.get('cost'))
        if cost == 0.0:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        comment = request.data.get('comment')
        if comment and len(comment) > 128:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        customer.add_balance(
            profile=request.user,
            cost=cost,
            comment=' '.join(comment.split()) if comment else gettext('fill account through admin side')
        )
        customer.save(update_fields=('balance',))
        return Response()


class CustomersGroupsListAPIView(DjingListAPIView):
    pagination_class = QueryPageNumberPagination
    serializer_class = serializers.CustomerGroupSerializer
    filter_backends = (OrderingFilter,)
    ordering_fields = ('title', 'usercount')

    def get_queryset(self):
        return get_objects_for_user(
            self.request.user,
            'groupapp.view_group', klass=Group,
            use_groups=False,
            accept_global_perms=False
        ).annotate(usercount=Count('customer'))


class PassportInfoModelViewSet(DjingModelViewSet):
    queryset = models.PassportInfo.objects.defer('customer')
    serializer_class = serializers.PassportInfoModelSerializer


class InvoiceForPaymentModelViewSet(DjingModelViewSet):
    queryset = models.InvoiceForPayment.objects.select_related(
        'customer', 'author'
    )
    serializer_class = serializers.InvoiceForPaymentModelSerializer
    filterset_fields = ('customer',)


class CustomerRawPasswordModelViewSet(DjingModelViewSet):
    queryset = models.CustomerRawPassword.objects.select_related(
        'customer'
    )
    serializer_class = serializers.CustomerRawPasswordModelSerializer


class AdditionalTelephoneModelViewSet(DjingModelViewSet):
    queryset = models.AdditionalTelephone.objects.defer('customer')
    serializer_class = serializers.AdditionalTelephoneModelSerializer
    filterset_fields = 'customer',


class PeriodicPayForIdModelViewSet(DjingModelViewSet):
    queryset = models.PeriodicPayForId.objects.defer('account')
    serializer_class = serializers.PeriodicPayForIdModelSerializer


class AttachServicesToGroups(APIView):
    if getattr(settings, 'DEBUG', False):
        from rest_framework.authentication import SessionAuthentication
        authentication_classes = TokenAuthentication, SessionAuthentication
    else:
        authentication_classes = TokenAuthentication,
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request, format=None):
        del format
        gid = safe_int(request.query_params.get('group'))
        grp = get_object_or_404(Group, pk=gid)

        selected_services_id = tuple(
            pk[0] for pk in grp.service_set.only('pk').values_list('pk')
        )
        services = Service.objects.only('pk', 'title').iterator()
        return Response(({
            'service': srv.pk,
            'service_name': srv.title,
            'check': srv.pk in selected_services_id
        } for srv in services))

    def post(self, request, format=None):
        del format
        group = safe_int(request.query_params.get('group'))
        group = get_object_or_404(Group, pk=group)
        selected_service_ids_db = frozenset(t.pk for t in group.service_set.only('pk'))
        all_available_service_ids_db = frozenset(srv.pk for srv in Service.objects.only('pk').iterator())

        # list of dicts: service<int>, check<bool>
        data = request.data
        selected_service_ids = frozenset(s.get('service') for s in data
                                         if isinstance(s.get('service'), int) and
                                         s.get('check') and
                                         s.get('service') in all_available_service_ids_db)

        # add = selected_service_ids - selected_service_ids_db
        sub = all_available_service_ids_db - (selected_service_ids - selected_service_ids_db)

        group.service_set.set(selected_service_ids)
        models.Customer.objects.filter(
            group=group,
            last_connected_service__in=sub
        ).update(last_connected_service=None)
        return Response(status=status.HTTP_200_OK)


class DhcpLever(SecureApiView):
    #
    # Api view for dhcp event
    #
    http_method_names = ('get',)

    def get(self, request, format=None):
        del format
        data = request.query_params.copy()
        try:
            r = self.on_dhcp_event(data)
            if r is not None:
                if issubclass(r.__class__, Exception):
                    return Response({'error': str(r)})
                return Response({'text': r})
            return Response({'status': 'ok'})
        except IntegrityError as e:
            return Response({
                'status': str(e).replace('\n', ' ')
            })

    @staticmethod
    def on_dhcp_event(data: dict):
        """
        :param data = {
            'client_ip': ip_address('127.0.0.1'),
            'client_mac': 'aa:bb:cc:dd:ee:ff',
            'switch_mac': 'aa:bb:cc:dd:ee:ff',
            'switch_port': 3,
            'cmd': 'commit'
        }"""
        try:
            action = data.get('cmd')
            if action is None:
                return '"cmd" parameter is missing'
            client_ip = data.get('client_ip')
            if client_ip is None:
                return '"client_ip" parameter is missing'
            if action == 'commit':
                return dhcp_commit(
                    client_ip, data.get('client_mac'),
                    data.get('switch_mac'), data.get('switch_port')
                )
            elif action == 'expiry':
                return dhcp_expiry(client_ip)
            elif action == 'release':
                return dhcp_release(client_ip)
            else:
                return '"cmd" parameter is invalid: %s' % action
        except (LogicError, DuplicateEntry) as e:
            print('%s:' % e.__class__.__name__, e)
            return str(e)
