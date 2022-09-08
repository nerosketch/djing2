from collections import OrderedDict
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action, api_view
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from djing2.lib.filters import CustomSearchFilter
from djing2.permissions import IsSuperUser
from djing2.lib import safe_float, safe_int
from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.lib.mixins import SitesFilterMixin
from djing2.viewsets import DjingModelViewSet
from customers import models, serializers
from customers.models import CustomerQuerySet
from customers.views.view_decorators import catch_customers_errs
from dynamicfields.views import AbstractDynamicFieldContentModelViewSet
from groupapp.models import Group
from profiles.models import UserProfileLogActionType
from services.models import OneShotPay, PeriodicPay, Service


class CustomerServiceModelViewSet(DjingModelViewSet):
    queryset = models.CustomerService.objects.all()
    serializer_class = serializers.CustomerServiceModelSerializer

    def create(self, request, *args, **kwargs):
        return Response(
            gettext("Not allowed to direct create Customer service, use 'pick_service' url"),
            status=status.HTTP_403_FORBIDDEN,
        )


class CustomerLogModelViewSet(DjingModelViewSet):
    queryset = models.CustomerLog.objects.select_related(
        "customer",
        "author"
    ).order_by('-id')
    serializer_class = serializers.CustomerLogModelSerializer
    filterset_fields = ("customer",)

    def create(self, request, *args, **kwargs):
        return Response(
            gettext("Not allowed to direct create Customer log"),
            status=status.HTTP_403_FORBIDDEN
        )


class CustomerModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = models.Customer.objects.select_related(
        "current_service", "current_service__service", "gateway"
    )
    serializer_class = serializers.CustomerModelSerializer
    filter_backends = [
        CustomObjectPermissionsFilter,
        DjangoFilterBackend,
        OrderingFilter,
        CustomSearchFilter
    ]
    search_fields = (
        "username",
        "fio",
        "telephone",
        "description"
    )
    filterset_fields = (
        "group",
        "device",
        "dev_port",
        "current_service__service",
        "address",
        "is_active"
    )
    ordering_fields = (
        "username",
        "fio",
        "balance",
        "current_service__service__title",
        "birth_day"
    )

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.annotate(
            lease_count=Count("customeripleasemodel"),
            octsum=Sum(
                "traf_cache__octets",
                filter=Q(
                    traf_cache__event_time__gt=datetime.now() - timedelta(minutes=5)
                )
            ),
        )

    def filter_queryset(self, queryset: CustomerQuerySet):
        queryset = super().filter_queryset(queryset=queryset)

        house = safe_int(self.request.query_params.get('house'))
        if house > 0:
            return queryset.filter_customers_by_addr(
                addr_id=house,
            )
        else:
            street = safe_int(self.request.query_params.get('street'))
            if street > 0:
                return queryset.filter_customers_by_addr(
                    addr_id=street,
                )

        address = safe_int(self.request.query_params.get('address'))
        if address > 0:
            return queryset.filter_customers_by_addr(
                addr_id=address,
            )

        return queryset

    def perform_create(self, serializer, *args, **kwargs):
        customer_instance = super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )
        if customer_instance is not None:
            # log about creating new customer
            self.request.user.log(
                do_type=UserProfileLogActionType.CREATE_USER,
                additional_text='%s, "%s", %s'
                % (
                    customer_instance.username,
                    customer_instance.fio,
                    customer_instance.group.title if customer_instance.group else "",
                ),
            )
        return customer_instance

    def perform_destroy(self, instance):
        # log about deleting customer
        self.request.user.log(
            do_type=UserProfileLogActionType.DELETE_USER,
            additional_text=(
                '%(uname)s, "%(fio)s", %(addr)s'
                % {
                    "uname": instance.username,
                    "fio": instance.fio or "-",
                    "addr": instance.full_address,
                }
            ).strip(),
        )
        return super().perform_destroy(instance)

    @action(methods=["post"], detail=True)
    @catch_customers_errs
    def pick_service(self, request, pk=None):
        del pk
        self.check_permission_code(request, "customers.can_buy_service")
        service_id = safe_int(request.data.get("service_id"))
        deadline = request.data.get("deadline")
        srv = get_object_or_404(Service, pk=service_id)
        customer = self.get_object()
        log_comment = None
        if deadline:
            datetime_fmt = getattr(api_settings, "DATETIME_FORMAT", "%Y-%m-%d %H:%M")
            deadline = datetime.strptime(deadline, datetime_fmt)
            log_comment = _("Service '%(service_name)s' has connected via admin until %(deadline)s") % {
                "service_name": srv.title,
                "deadline": deadline,
            }
        try:
            customer.pick_service(
                service=srv,
                author=request.user,
                comment=log_comment,
                deadline=deadline,
                allow_negative=True
            )
        except models.NotEnoughMoney as e:
            return Response(data=str(e), status=status.HTTP_402_PAYMENT_REQUIRED)
        return Response(status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True)
    @catch_customers_errs
    def make_shot(self, request, pk=None):
        customer = self.get_object()
        shot_id = safe_int(request.data.get("shot_id"))
        shot = get_object_or_404(OneShotPay, pk=shot_id)
        shot.before_pay(request=request, customer=customer)
        r = customer.make_shot(request, shot, allow_negative=True)
        shot.after_pay(request=request, customer=customer)
        if not r:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(r)

    @action(methods=["post"], detail=True)
    @catch_customers_errs
    def make_periodic_pay(self, request, pk=None):
        periodic_pay_request_serializer = serializers.PeriodicPayForIdRequestSerializer(data=request.data)
        periodic_pay_request_serializer.is_valid(raise_exception=True)
        periodic_pay_id = periodic_pay_request_serializer.data.get("periodic_pay_id")
        next_pay_date = periodic_pay_request_serializer.data.get("next_pay")
        if not all([periodic_pay_id, next_pay_date]):
            return Response("Invalid data", status=status.HTTP_400_BAD_REQUEST)
        customer = self.get_object()
        periodic_pay = get_object_or_404(PeriodicPay, pk=periodic_pay_id)
        customer.make_periodic_pay(periodic_pay=periodic_pay, next_pay=next_pay_date)
        return Response("ok")

    @make_periodic_pay.mapping.get
    def make_periodic_pay_get(self, request, **kwargs):
        periodic_pay_request_serializer = serializers.PeriodicPayForIdRequestSerializer()
        return Response(periodic_pay_request_serializer.data)

    @action(detail=False)
    @catch_customers_errs
    def service_users(self, request):
        service_id = safe_int(request.query_params.get("service_id"))
        if service_id == 0:
            return Response("service_id is required", status=status.HTTP_403_FORBIDDEN)
        qs = models.Customer.objects.filter(current_service__service_id=service_id)
        if not request.user.is_superuser:
            qs = qs.filter(sites__in=[self.request.site])
        qs = qs.values("id", "group_id", "username", "fio")
        return Response(qs)

    @action(detail=True)
    @catch_customers_errs
    def stop_service(self, request, pk=None):
        del pk
        self.check_permission_code(request, "customers.can_complete_service")
        customer = self.get_object()
        cust_srv = customer.active_service()
        if cust_srv is None:
            return Response(data=_("Service not connected"))

        srv = cust_srv.service
        if srv is None:
            return Response(
                "Custom service has not service (Look at customers.views.admin_site)",
                status=status.HTTP_400_BAD_REQUEST
            )

        customer.stop_service(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True)
    @catch_customers_errs
    def ping_all_ips(self, request, pk=None):
        self.check_permission_code(request, "customers.can_ping")
        del request, pk
        customer = self.get_object()
        res_text, res_status = customer.ping_all_leases()
        return Response({"text": res_text, "status": res_status})

    @action(detail=True)
    @catch_customers_errs
    def current_service(self, request, pk=None):
        del request, pk
        customer = self.get_object()
        if not customer.current_service:
            return Response(False)
        curr_srv = customer.current_service
        cur_ser_cls = serializers.CustomerServiceModelSerializer
        cur_ser_cls.Meta.depth = 1
        cur_ser = cur_ser_cls(instance=curr_srv)
        return Response(cur_ser.data)

    @action(methods=["post"], detail=True)
    @catch_customers_errs
    def add_balance(self, request, pk=None):
        del pk
        self.check_permission_code(request, "customers.can_add_balance")

        cost = safe_float(request.data.get("cost"))
        if cost == 0.0:
            return Response("Passed invalid cost parameter", status=status.HTTP_400_BAD_REQUEST)

        if cost > 0.0:
            self.check_permission_code(
                request,
                "customers.can_add_balance",
                _("You can't top up an account with a positive amount")
            )
        else:
            self.check_permission_code(
                request,
                "customers.can_add_negative_balance",
                _("You can't top up an account with a negative amount"),
            )

        customer = self.get_object()

        comment = request.data.get("comment")
        if comment and len(comment) > 128:
            return Response(
                "comment parameter is too long",
                status=status.HTTP_400_BAD_REQUEST
            )

        customer.add_balance(
            profile=request.user,
            cost=cost,
            comment=" ".join(comment.split()) if comment else gettext("fill account through admin side"),
        )
        customer.save(update_fields=("balance",))
        return Response()

    @action(methods=["post"], detail=True)
    @catch_customers_errs
    def set_service_group_accessory(self, request, pk=None):
        # customer = self.get_object()
        group_id = request.data.get("group_id")
        if not group_id:
            return Response(
                "group_id is required",
                status=status.HTTP_400_BAD_REQUEST
            )
        group = get_object_or_404(Group, pk=int(group_id))
        wanted_service_ids = request.data.get("services")
        models.Customer.set_service_group_accessory(
            group,
            wanted_service_ids,
            request
        )
        return Response()

    @action(detail=False)
    @catch_customers_errs
    def filter_device_port(self, request):
        dev_id = request.query_params.get("device_id")
        port_id = request.query_params.get("port_id")
        if not all([dev_id, port_id]):
            return Response(
                "Required paramemters: [dev_id, port_id]",
                status=status.HTTP_400_BAD_REQUEST
            )
        customers = models.Customer.objects.filter(
            device_id=dev_id,
            dev_port_id=port_id
        )
        return Response(self.get_serializer(customers, many=True).data)

    @action(methods=["put"], detail=True)
    @catch_customers_errs
    def passport(self, request, pk=None):
        self.serializer_class = serializers.PassportInfoModelSerializer
        passport_obj = models.PassportInfo.objects.filter(customer_id=pk).first()

        if passport_obj is None:
            # create passport info for customer
            serializer = serializers.PassportInfoModelSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            models.PassportInfo.objects.create(
                customer=self.get_object(),
                **serializer.validated_data
            )
            res_stat = status.HTTP_201_CREATED
        else:
            # change passport info for customer
            serializer = serializers.PassportInfoModelSerializer(
                instance=passport_obj,
                data=request.data
            )
            serializer.is_valid(raise_exception=True)
            serializer.update(
                instance=passport_obj,
                validated_data=serializer.validated_data
            )
            res_stat = status.HTTP_200_OK

        return Response(serializer.data, status=res_stat)

    @passport.mapping.get
    def passport_get(self, request, pk=None):
        self.serializer_class = serializers.PassportInfoModelSerializer
        passport_obj = models.PassportInfo.objects.filter(customer_id=pk).first()
        ser = serializers.PassportInfoModelSerializer(instance=passport_obj)
        return Response(ser.data)

    @action(detail=False)
    def service_type_report(self, request):
        self.check_permission_code(
            request,
            "customers.can_view_service_type_report"
        )
        r = models.Customer.objects.customer_service_type_report()
        return Response(r)

    @action(detail=False)
    def activity_report(self, request):
        self.check_permission_code(request, "customers.can_view_activity_report")
        r = models.Customer.objects.activity_report()
        return Response(r)

    @action(methods=["get"], detail=True)
    def is_access(self, request, pk=None):
        customer = self.get_object()
        is_acc = customer.is_access()
        return Response(is_acc)

    @action(methods=["get"], detail=False)
    def generate_password(self, request):
        rp = serializers.generate_random_password()
        return Response(rp)

    @action(methods=["post"], detail=True)
    def set_markers(self, request, pk=None):
        customer = self.get_object()
        flag_names = list(request.data)
        mflags = tuple(f for f, n in models.Customer.MARKER_FLAGS)
        for flag_name in flag_names:
            if flag_name not in mflags:
                return Response(
                    'Bad "flags". Must be an array of flag names. Such as %s' % mflags,
                    status=status.HTTP_400_BAD_REQUEST,
                )
        customer.set_markers(flag_names=flag_names)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False)
    def get_afk(self, request):
        date_fmt = getattr(api_settings, "DATETIME_FORMAT", "%Y-%m-%d %H:%M")

        date_limit = request.query_params.get('date_limit')
        if date_limit is not None:
            date_limit = datetime.strptime(date_limit, date_fmt)

        out_limit = request.query_params.get('out_limit')
        out_limit = safe_int(out_limit, 50)

        afk = models.Customer.objects.filter_afk(
            date_limit=date_limit,
            out_limit=out_limit
        )

        locality_addr = request.query_params.get('locality', 0)
        locality_addr = safe_int(locality_addr)
        if locality_addr > 0:
            addr_filtered_customers = models.Customer.objects.filter_customers_by_addr(
                addr_id=locality_addr
            ).only('pk').values_list('pk', flat=True)
            afk = tuple(c for c in afk if c.customer_id in addr_filtered_customers)
            del addr_filtered_customers

        res_afk = (OrderedDict(
            timediff=str(r.timediff),
            last_date=r.last_date.strftime(date_fmt),
            customer_id=r.customer_id,
            customer_uname=r.customer_uname,
            customer_fio=r.customer_fio
        ) for r in afk)
        return Response({
            'count': 1,
            'next': None,
            'previous': None,
            'results': res_afk
        })

    @action(methods=['get'], detail=False)
    def bums(self, request):
        qs = self.get_queryset().filter(address=None)
        queryset = self.filter_queryset(qs)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InvoiceForPaymentModelViewSet(DjingModelViewSet):
    queryset = models.InvoiceForPayment.objects.select_related("customer", "author")
    serializer_class = serializers.InvoiceForPaymentModelSerializer
    filterset_fields = ("customer",)


class CustomerRawPasswordModelViewSet(DjingModelViewSet):
    queryset = models.CustomerRawPassword.objects.select_related("customer")
    serializer_class = serializers.CustomerRawPasswordModelSerializer
    filterset_fields = ("customer",)


class AdditionalTelephoneModelViewSet(DjingModelViewSet):
    queryset = models.AdditionalTelephone.objects.defer("customer")
    serializer_class = serializers.AdditionalTelephoneModelSerializer
    filterset_fields = ("customer",)


class PeriodicPayForIdModelViewSet(DjingModelViewSet):
    queryset = models.PeriodicPayForId.objects.defer("account").select_related("periodic_pay")
    serializer_class = serializers.PeriodicPayForIdModelSerializer
    filterset_fields = ("account",)


class AttachServicesToGroups(APIView):
    if getattr(settings, "DEBUG", False):
        from rest_framework.authentication import SessionAuthentication

        authentication_classes = (TokenAuthentication, SessionAuthentication)
    else:
        authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, IsAdminUser)

    @staticmethod
    def get(request, format=None):
        del format
        gid = safe_int(request.query_params.get("group"))
        grp = get_object_or_404(Group, pk=gid)

        selected_services_id = tuple(pk[0] for pk in grp.service_set.only("pk").values_list("pk"))
        services = Service.objects.only("pk", "title").iterator()
        return Response(
            {"service": srv.pk, "service_name": srv.title, "check": srv.pk in selected_services_id} for srv in services
        )

    @staticmethod
    def post(request, format=None):
        del format
        group = safe_int(request.query_params.get("group"))
        group = get_object_or_404(Group, pk=group)
        # selected_service_ids_db = frozenset(t.pk for t in group.service_set.only('pk'))
        all_available_service_ids_db = frozenset(srv.pk for srv in Service.objects.only("pk").iterator())

        # list of dicts: service<int>, check<bool>
        data = request.data
        selected_service_ids = frozenset(
            s.get("service")
            for s in data
            if isinstance(s.get("service"), int)
            and s.get("check")
            and s.get("service") in all_available_service_ids_db
        )

        # add = selected_service_ids - selected_service_ids_db
        # sub = all_available_service_ids_db - (selected_service_ids - selected_service_ids_db)

        group.service_set.set(selected_service_ids)
        # models.Customer.objects.filter(
        #     group=group,
        #     last_connected_service__in=sub
        # ).update(last_connected_service=None)
        return Response(status=status.HTTP_200_OK)


class CustomerAttachmentViewSet(DjingModelViewSet):
    queryset = models.CustomerAttachment.objects.select_related("author")
    serializer_class = serializers.CustomerAttachmentSerializer
    filterset_fields = ("customer",)

    def perform_create(self, serializer, *args, **kwargs) -> None:
        serializer.save(author=self.request.user)


class CustomerDynamicFieldContentModelViewSet(AbstractDynamicFieldContentModelViewSet):
    queryset = models.CustomerDynamicFieldContentModel.objects.select_related('field')

    def get_group_id(self) -> int:
        customer_id = self.request.query_params.get('customer')
        self.customer_id = customer_id
        customer = get_object_or_404(models.Customer.objects.only('group_id'), pk=customer_id)
        self.customer = customer
        return customer.group_id

    def filter_content_fields_queryset(self):
        return self.get_queryset().filter(
            customer_id=self.customer_id,
        )

    def create_content_field_kwargs(self, field_data):
        if hasattr(self, 'customer_id'):
            return {
                'customer_id': self.customer_id
            }
        return {
            'customer_id': field_data.get('customer')
        }


@api_view(['get'])
def groups_with_customers(request):
    # TODO: Also filter by address
    grps = Group.objects.annotate(
        customer_count=Count('customer')
    ).filter(
        customer_count__gt=0
    ).order_by('title')
    ser = serializers.GroupsWithCustomersSerializer(instance=grps, many=True)
    return Response(ser.data)


class SuperUserGetCustomerTokenByPhoneAPIView(APIView):
    throttle_classes = ()
    permission_classes = (IsAuthenticated, IsSuperUser)
    serializer_class = serializers.SuperUserGetCustomerTokenByPhoneSerializer

    def get(self, request, *args, **kwargs):
        ser = self.serializer_class(data=request.query_params)
        ser.is_valid(raise_exception=True)
        dat = ser.data
        tel = dat.get('telephone')
        #  customers = models.Customer.objects.filter(telephone=)
        tel = models.AdditionalTelephone.objects.filter(
            Q(telephone=tel), Q(customer__telephone=tel)
        ).select_related('customer').first()
        if tel:
            user = tel.customer
            token = Token.objects.filter(user=user).first()
            if token:
                return Response({"token": token.key})
        return Response(status=status.HTTP_204_NO_CONTENT)

