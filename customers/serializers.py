from string import digits, ascii_lowercase
from random import choice

# from django.contrib.auth.hashers import make_password
# from django.utils.translation import gettext_lazy as _
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
        fields = '__all__'


class CustomerStreetModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomerStreet
        fields = '__all__'


class CustomerLogModelSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_short_name', read_only=True)
    # customer_name = serializers.CharField(source='customer.get_short_name')

    class Meta:
        model = models.CustomerLog
        fields = '__all__'


class CustomerModelSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    group_title = serializers.CharField(source='group.title', read_only=True)
    street_name = serializers.CharField(source='street.name', read_only=True)
    gateway_title = serializers.CharField(source='gateway.title', read_only=True)
    device_comment = serializers.CharField(source='device.comment', read_only=True)
    service_title = serializers.CharField(source='current_service.service.title', read_only=True)

    def create(self, validated_data):
        # raw_password = validated_data.get('password')
        validated_data.update({
            'is_admin': False,
            'is_superuser': False
            # 'password': make_password(raw_password)
        })
        acc = super().create(validated_data)
        # try:
        #     acc_passw = models.CustomerRawPassword.objects.get(customer=acc)
        #     acc_passw.passw_text = raw_password
        #     acc_passw.save(update_fields=('passw_text',))
        # except models.CustomerRawPassword.DoesNotExist:
        #     models.CustomerRawPassword.objects.create(
        #         customer=acc,
        #         passw_text=raw_password
        #     )
        return acc

    class Meta:
        model = models.Customer
        fields = (
            'pk', 'username', 'telephone', 'fio',
            'group', 'group_title', 'balance', 'ip_address', 'description', 'street', 'street_name',
            'house', 'is_active', 'gateway', 'gateway_title', 'auto_renewal_service',
            'device', 'device_comment', 'dev_port', 'last_connected_service', 'current_service',
            'service_title', 'is_dynamic_ip', 'full_name'
        )


class CustomerGroupSerializer(GroupsSerializer):
    usercount = serializers.IntegerField(source='customer_set.count', read_only=True)

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
        exclude = ('account',)


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
