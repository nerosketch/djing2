from string import digits, ascii_lowercase
from random import choice

from django.contrib.auth.hashers import make_password
# from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from customers import models
from djing2.lib import safe_int


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
        models.Subscriber.objects.get(username=username)
        return generate_random_username()
    except models.Subscriber.DoesNotExist:
        return safe_int(username)


def generate_random_password():
    return _generate_random_chars(length=6, chars=digits + ascii_lowercase)


class SubscriberServiceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubscriberService
        fields = '__all__'


class SubscriberStreetModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubscriberStreet
        fields = '__all__'


class SubscriberLogModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubscriberLog
        fields = '__all__'


class SubscriberModelSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=127)
    password = serializers.CharField(max_length=64)

    def create(self, validated_data):
        raw_password = validated_data.get('password')
        acc = super().create(validated_data)
        acc.password = make_password(raw_password)
        try:
            acc_passw = models.SubscriberRawPassword.objects.get(subscriber=acc)
            acc_passw.passw_text = raw_password
            acc_passw.save(update_fields=('passw_text',))
        except models.SubscriberRawPassword.DoesNotExist:
            models.SubscriberRawPassword.objects.create(
                passw_text=raw_password
            )
        return acc

    class Meta:
        model = models.Subscriber
        fields = (
            'username', 'password', 'telephone', 'fio',
            'group', 'description', 'street',
            'house', 'is_active', 'gateway'
        )


class PassportInfoModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PassportInfo
        exclude = ('subscriber',)


class InvoiceForPaymentModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InvoiceForPayment
        fields = '__all__'


class SubscriberRawPasswordModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubscriberRawPassword
        fields = '__all__'


class AdditionalTelephoneModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AdditionalTelephone
        exclude = ('subscriber',)


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