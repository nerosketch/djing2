# Generated by Django 3.1.12 on 2021-09-14 14:31

from django.db import migrations, models

from addresses.interfaces import IAddressObject
from djing2.models import BaseAbstractModelMixin


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('groupapp', '0002_group_sites'),
        ('customers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parent_addr', models.ForeignKey(
                    'self', verbose_name='Parent address',
                    on_delete=models.SET_DEFAULT,
                    null=True,
                    blank=True,
                    default=None
                )),
                ('address_type', models.PositiveSmallIntegerField(
                    verbose_name='Address type',
                    choices=((0, 'Choices'), (4, 'Locality'), (9, 'Street'), (12, 'House'), (16, 'Building')),
                    default=0
                )),
                ('title', models.CharField('Title', max_length=128)),
            ],
            options={
                'db_table': 'addresses',
                'unique_together': ('parent_addr', 'address_type', 'title')
            },
            bases=(IAddressObject, BaseAbstractModelMixin, models.Model),
        ),
    ]
