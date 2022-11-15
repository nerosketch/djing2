import re

from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext as _
from rest_framework import serializers

from profiles.models import split_fio
from profiles.serializers import BaseAccountSerializer, generate_random_password
from customers import models
from .schemas import update_passw


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

    # TODO: deprecated, defined in profiles.schemas.BaseAccountSchema
    @staticmethod
    def validate_fio(full_fio: str) -> str:
        def _is_chunk_ok(v: str, rgxp=re.compile(r"^[A-Za-zА-Яа-яЁё-]{1,250}$")):
            return bool(rgxp.search(v))

        err_text = _('Credentials must be without spaces or any special symbols, only letters and "-"')

        r = split_fio(full_fio)
        if r.surname is not None and not _is_chunk_ok(r.surname):
            raise serializers.ValidationError(err_text)
        if r.name is not None and not _is_chunk_ok(r.name):
            raise serializers.ValidationError(err_text)
        if r.last_name is not None and not _is_chunk_ok(r.last_name):
            raise serializers.ValidationError(err_text)

        return f"{r.surname} {r.name} {r.last_name or ''}"

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
