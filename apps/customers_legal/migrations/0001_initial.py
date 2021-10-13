# Generated by Django 3.1.12 on 2021-10-13 13:31

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import djing2.models
import dynamicfields.models
import re


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('addresses', '0001_initial'),
        ('profiles', '0005_auto_20210204_2043'),
        ('customers', '0015_change_street'),
        ('groupapp', '0002_group_sites'),
        ('dynamicfields', '0002_tags_20210908_1318'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerLegalModel',
            fields=[
                ('baseaccount_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='profiles.baseaccount')),
                ('balance', models.FloatField(default=0.0)),
                ('tax_number', models.CharField(max_length=32, validators=[django.core.validators.RegexValidator(re.compile('^-?\\d+\\Z'), code='invalid', message='Enter a valid integer.')], verbose_name='Tax number')),
                ('post_index', models.CharField(blank=True, default=None, help_text='почтовый индекс адреса абонента', max_length=32, null=True, verbose_name='Post number')),
                ('actual_start_time', models.DateTimeField(help_text='дата начала интервала, на котором актуальна информация', verbose_name='Actual start time')),
                ('actual_end_time', models.DateTimeField(blank=True, default=None, help_text='дата окончания интервала, на котором актуальна информация', null=True, verbose_name='Actual end time')),
                ('title', models.CharField(max_length=256, verbose_name='Title')),
                ('description', models.TextField(blank=True, default=None, null=True, verbose_name='Comment')),
                ('address', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='addresses.addressmodel', verbose_name='Address')),
                ('branches', models.ManyToManyField(blank=True, to='customers.Customer', verbose_name='Branches')),
                ('group', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='groupapp.group', verbose_name='Legal customer group')),
            ],
            options={
                'db_table': 'customers_legal',
            },
            bases=('profiles.baseaccount',),
        ),
        migrations.CreateModel(
            name='LegalCustomerPostAddressModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('post_index', models.CharField(blank=True, default=None, max_length=32, null=True, verbose_name='Post number')),
                ('office_num', models.CharField(max_length=32, verbose_name='Office number')),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='addresses.addressmodel', verbose_name='Address')),
                ('legal_customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers_legal.customerlegalmodel')),
            ],
            options={
                'db_table': 'customer_legal_post_address',
            },
            bases=(djing2.models.BaseAbstractModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='LegalCustomerDeliveryAddressModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='addresses.addressmodel', verbose_name='Address')),
                ('legal_customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers_legal.customerlegalmodel')),
            ],
            options={
                'db_table': 'customer_legal_delivery_address',
            },
            bases=(djing2.models.BaseAbstractModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='LegalCustomerBankModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=64, verbose_name='Title')),
                ('post_index', models.CharField(blank=True, default=None, help_text='Почтовый индекс почтового адреса абонента', max_length=32, null=True, verbose_name='Post number')),
                ('number', models.CharField(max_length=64, verbose_name='Bank account number')),
                ('legal_customer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='customers_legal.customerlegalmodel')),
            ],
            options={
                'db_table': 'customer_legal_bank',
            },
            bases=(djing2.models.BaseAbstractModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='CustomerLegalTelephoneModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telephone', models.CharField(max_length=16, unique=True, validators=[django.core.validators.RegexValidator('^(\\+[7893]\\d{10,11})?$')], verbose_name='Telephone')),
                ('owner_name', models.CharField(max_length=127)),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('last_change_time', models.DateTimeField(blank=True, null=True)),
                ('legal_customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers_legal.customerlegalmodel')),
            ],
            options={
                'db_table': 'customer_legal_additional_telephones',
            },
            bases=(djing2.models.BaseAbstractModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='CustomerLegalDynamicFieldContentModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', dynamicfields.models._DynamicField(blank=True, max_length=512, null=True)),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='dynamicfields.fieldmodel')),
                ('legal_customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers_legal.customerlegalmodel')),
            ],
            options={
                'db_table': 'customers_legal_dynamic_content',
            },
        ),
    ]
