import os
import re
from datetime import datetime, timedelta

from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext as _
from rest_framework import serializers

from groupapp.models import Group
from profiles.models import split_fio
from profiles.serializers import BaseAccountSerializer, generate_random_password
from customers import models
from djing2.lib.mixins import BaseCustomModelSerializer
from services.serializers import ServiceModelSerializer
from .schemas import update_passw


class CustomerServiceModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerService
        fields = '__all__'


# TODO: deprecated: defined in customers.schemas.CustomerModelSchema
class CustomerModelSerializer(BaseAccountSerializer):
    group_title = serializers.CharField(source="group.title", read_only=True)

    # TODO: optimize it
    address_title = serializers.CharField(source='full_address', read_only=True)

    # gateway_title = serializers.CharField(source="gateway.title", read_only=True)
    device_comment = serializers.CharField(source="device.comment", read_only=True)
    last_connected_service_title = serializers.CharField(source="last_connected_service.title", read_only=True)
    current_service_title = serializers.CharField(source="current_service.service.title", read_only=True)
    service_id = serializers.IntegerField(source="current_service.service.id", read_only=True)
    raw_password = serializers.CharField(source="customerrawpassword.passw_text", read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False, read_only=True)
    create_date = serializers.CharField(read_only=True)
    lease_count = serializers.IntegerField(read_only=True)

    marker_icons = serializers.ListField(source="get_flag_icons", child=serializers.CharField(), read_only=True)

    def create(self, validated_data):
        validated_data.update(
            {
                "is_admin": False,
                "is_superuser": False
                # 'password': make_password(raw_password)
            }
        )
        acc = super().create(validated_data)
        raw_password = validated_data.get("password")
        if raw_password is None:
            raw_password = generate_random_password()
        update_passw(acc, raw_password=raw_password)
        return acc

    def update(self, instance, validated_data):
        raw_password = validated_data.get("password")
        if raw_password:
            # try:
            # validate_password(raw_password, instance)
            update_passw(acc=instance, raw_password=raw_password)
            validated_data["password"] = make_password(raw_password)
            # except DjangoValidationError as err:
            #     raise DRFValidationError(err)

        instance = super().update(instance, validated_data)

        return instance

    @staticmethod
    def validate_fio(full_fio: str) -> str:
        def _is_chunk_ok(v: str, rgxp=re.compile(r"^[A-Za-zА-Яа-яЁё-]{1,250}$")):
            r = rgxp.search(v)
            return bool(r)

        err_text = _('Credentials must be without spaces or any special symbols, only letters and "-"')

        res = split_fio(full_fio)
        if len(res) == 3:
            surname, name, last_name = res
            if surname is not None and not _is_chunk_ok(surname):
                raise serializers.ValidationError(err_text)
            if name is not None and not _is_chunk_ok(name):
                raise serializers.ValidationError(err_text)
            if last_name is not None and not _is_chunk_ok(last_name):
                raise serializers.ValidationError(err_text)

            return f"{surname} {name} {last_name or ''}"
        else:
            raise serializers.ValidationError(_('3 words required: surname, name and last_name without spaces'))

    class Meta:
        model = models.Customer
        # depth = 1
        exclude = (
            'groups',
            'user_permissions',
            'markers',
            'is_superuser',
            'is_admin',
        )


class PassportInfoModelSerializer(BaseCustomModelSerializer):
    registration_address_title = serializers.CharField(source='full_address', read_only=True)

    @staticmethod
    def validate_date_of_acceptance(value):
        now = datetime.now().date()
        old_date = datetime.now() - timedelta(days=365 * 100)
        if value >= now:
            raise serializers.ValidationError(_("You can't specify the future"))
        elif value <= old_date.date():
            raise serializers.ValidationError(_("Too old date. Must be newer than %s") % old_date.strftime('%Y-%m-%d %H:%M:%S'))
        return value

    class Meta:
        model = models.PassportInfo
        exclude = ("customer",)
        extra_kwargs = {
            'distributor': {
                'initial': os.getenv(
                    'CUSTOMERS_PASSPORT_DEFAULT_DISTRIBUTOR',
                    'customers passport default distributor'
                )
            }
        }


class InvoiceForPaymentModelSerializer(BaseCustomModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    author_uname = serializers.CharField(source="author.username", read_only=True)
    cost = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)

    class Meta:
        model = models.InvoiceForPayment
        fields = "__all__"


class PeriodicPayForIdRequestSerializer(serializers.Serializer):
    periodic_pay_id = serializers.IntegerField()
    next_pay = serializers.DateTimeField()


"""class AmountMoneySerializer(serializers.Serializer):
    amount = serializers.FloatField(max_value=5000)
    comment = serializers.CharField(
        max_length=128,
        required=False
    )

    def create(self, validated_data):
        amnt = validated_data.get('amount')
        comment = validated_data.get('comment')
        if not comment:
            comment = _('fill account through admin side')
        raise NotImplementedError('`create()` must be implemented.')

    # def update(self, instance, validated_data):
    #     pass
"""


class GroupsWithCustomersSerializer(serializers.ModelSerializer):
    customer_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = ("id", "title", "customer_count")
