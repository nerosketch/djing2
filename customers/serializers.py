from string import digits, ascii_lowercase
from random import choice

from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from customers import models
from djing2.lib import safe_int
from groupapp.serializers import GroupsSerializer


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
        return safe_int(username)


def generate_random_password():
    return _generate_random_chars(length=6, chars=digits + ascii_lowercase)


class CustomerServiceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomerService
        fields = ('service', 'start_time', 'deadline')


class CustomerStreetModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomerStreet
        fields = ('id', 'name', 'group')


class CustomerLogModelSerializer(serializers.ModelSerializer):
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


class CustomerModelSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    group_title = serializers.CharField(source='group.title', read_only=True)
    street_name = serializers.CharField(source='street.name', read_only=True)
    gateway_title = serializers.CharField(source='gateway.title', read_only=True)
    device_comment = serializers.CharField(source='device.comment', read_only=True)
    service_title = serializers.CharField(source='current_service.service.title', read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    raw_password = serializers.CharField(source='customerrawpassword.passw_text', read_only=True)

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
        fields = (
            'pk', 'username', 'telephone', 'fio',
            'group', 'group_title', 'balance', 'ip_address', 'description', 'street', 'street_name',
            'house', 'is_active', 'gateway', 'gateway_title', 'auto_renewal_service',
            'device', 'device_comment', 'dev_port', 'last_connected_service', 'current_service',
            'service_title', 'is_dynamic_ip', 'full_name', 'password', 'raw_password'
        )


class CustomerGroupSerializer(GroupsSerializer):
    usercount = serializers.IntegerField(read_only=True)

    class Meta(GroupsSerializer.Meta):
        fields = ('pk', 'title', 'code', 'usercount')


class PassportInfoModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PassportInfo
        exclude = ('customer',)


class InvoiceForPaymentModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InvoiceForPayment
        fields = '__all__'


class CustomerRawPasswordModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomerRawPassword
        fields = '__all__'


class AdditionalTelephoneModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AdditionalTelephone
        exclude = ('customer',)


class PeriodicPayForIdModelSerializer(serializers.ModelSerializer):
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
