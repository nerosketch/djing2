from string import digits, ascii_lowercase
from random import choice

from django.contrib.auth.hashers import make_password
from drf_queryfields import QueryFieldsMixin
from rest_framework import serializers

from customers import models
from djing2.lib import safe_int
from djing2.lib.mixins import BaseCustomModelSerializer
from groupapp.serializers import GroupsSerializer
from services.serializers import ServiceModelSerializer


def _generate_random_chars(length=6, chars=digits, split=2, delimiter=''):
    username = ''.join(choice(chars) for i in range(length))

    if split:
        username = delimiter.join(
            username[start:start + split]
            for start in range(0, len(username), split)
        )
    return username


def generate_random_username():
    username = _generate_random_chars()
    try:
        models.Customer.objects.get(username=username)
        return generate_random_username()
    except models.Customer.DoesNotExist:
        return str(safe_int(username))


def generate_random_password():
    return _generate_random_chars(length=6, chars=digits + ascii_lowercase)


class CustomerServiceModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerService
        fields = ('service', 'start_time', 'deadline')


class DetailedCustomerServiceModelSerializer(BaseCustomModelSerializer):
    service = ServiceModelSerializer(many=False, read_only=True)

    class Meta:
        model = models.CustomerService
        fields = ('service', 'start_time', 'deadline')


class CustomerStreetModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerStreet
        fields = ('pk', 'name', 'group')


class CustomerLogModelSerializer(BaseCustomModelSerializer):
    author_name = serializers.CharField(source='author.get_short_name', read_only=True)
    # customer_name = serializers.CharField(source='customer.get_short_name')

    class Meta:
        model = models.CustomerLog
        fields = (
            'customer', 'cost', 'author',
            'author_name', 'comment', 'date'
        )


def update_passw(acc, raw_password):
    if raw_password:
        updated_count = models.CustomerRawPassword.objects.filter(customer=acc).update(passw_text=raw_password)
        if updated_count == 0:
            models.CustomerRawPassword.objects.create(
                customer=acc,
                passw_text=raw_password
            )


class CustomerModelSerializer(QueryFieldsMixin, serializers.ModelSerializer):
    username = serializers.CharField(initial=generate_random_username)
    is_active = serializers.BooleanField(initial=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    group_title = serializers.CharField(source='group.title', read_only=True)
    street_name = serializers.CharField(source='street.name', read_only=True)
    gateway_title = serializers.CharField(source='gateway.title', read_only=True)
    device_comment = serializers.CharField(source='device.comment', read_only=True)
    last_connected_service_title = serializers.CharField(source='last_connected_service.title', read_only=True)
    service_title = serializers.CharField(
        source='current_service.service.title', read_only=True
    )
    service_id = serializers.IntegerField(
        source='current_service.service.id', read_only=True
    )
    # device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.exclude(group=None)[:12])
    password = serializers.CharField(write_only=True, required=False, initial=generate_random_password)
    raw_password = serializers.CharField(
        source='customerrawpassword.passw_text', read_only=True
    )
    balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, coerce_to_string=False, required=False
    )
    create_date = serializers.CharField(read_only=True)
    lease_count = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        validated_data.update({
            'is_admin': False,
            'is_superuser': False
            # 'password': make_password(raw_password)
        })
        acc = super().create(validated_data)
        raw_password = validated_data.get('password')
        update_passw(acc, raw_password=raw_password)
        return acc

    def update(self, instance, validated_data):
        raw_password = validated_data.get('password')
        update_passw(acc=instance, raw_password=raw_password)
        validated_data['password'] = make_password(raw_password)

        instance = super().update(instance, validated_data)

        return instance

    class Meta:
        model = models.Customer
        # depth = 1
        fields = (
            'pk', 'username', 'telephone', 'fio',
            'group', 'group_title', 'balance', 'description', 'street', 'street_name',
            'house', 'is_active', 'gateway', 'gateway_title', 'auto_renewal_service',
            'device', 'device_comment', 'dev_port', 'last_connected_service',
            'last_connected_service_title', 'current_service', 'service_title',
            'service_id', 'is_dynamic_ip', 'full_name', 'password', 'raw_password',
            'create_date', 'birth_day', 'lease_count', 'sites'
        )


class CustomerGroupSerializer(GroupsSerializer):
    usercount = serializers.IntegerField(read_only=True)

    class Meta(GroupsSerializer.Meta):
        fields = ('pk', 'title', 'code', 'usercount')


class PassportInfoModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.PassportInfo
        exclude = ('customer',)


class InvoiceForPaymentModelSerializer(BaseCustomModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_uname = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = models.InvoiceForPayment
        fields = '__all__'


class CustomerRawPasswordModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerRawPassword
        fields = '__all__'


class AdditionalTelephoneModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.AdditionalTelephone
        fields = '__all__'


class PeriodicPayForIdModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.PeriodicPayForId
        fields = ('id', 'last_pay', 'next_pay', 'periodic_pay')


'''class AmountMoneySerializer(serializers.Serializer):
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
'''


class RadiusCustomerServiceRequestSerializer(serializers.Serializer):
    customer_ip = serializers.CharField(max_length=32)
    password = serializers.CharField(max_length=32)


class CustomerAttachmentSerializer(BaseCustomModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    create_time = serializers.DateTimeField(read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)

    class Meta:
        model = models.CustomerAttachment
        fields = '__all__'
