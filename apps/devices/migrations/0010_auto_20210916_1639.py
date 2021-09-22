# Generated by Django 3.1.12 on 2021-09-16 16:39

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('addresses', '0001_initial'),
        ('devices', '0009_auto_20210817_1739'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='address',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='addresses.addressmodel'),
        ),
        migrations.AlterField(
            model_name='device',
            name='code',
            field=models.CharField(blank=True, default=None, max_length=64, null=True, verbose_name='Code'),
        ),
        migrations.AlterField(
            model_name='device',
            name='create_time',
            field=models.DateTimeField(default=datetime.datetime.now, verbose_name='Create time'),
        ),
        migrations.AlterField(
            model_name='device',
            name='dev_type',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Unknown Device'), (2, 'PON OLT'), (3, 'PON ONU BDCOM'), (5, 'OLT ZTE C320'), (6, 'Zte ONU F660'), (7, 'Zte ONU F601'), (9, 'DLink DGS-3120-24SC'), (1, 'DLink DGS-1100-10/ME'), (10, 'DLink DGS-1100-06/ME'), (11, 'DLink DGS-3627G'), (4, 'Eltex switch'), (8, 'Huawei switch'), (12, 'Huawei switch S5300')], default=0, verbose_name='Device type'),
        ),
        migrations.AlterField(
            model_name='port',
            name='create_time',
            field=models.DateTimeField(default=datetime.datetime.now, verbose_name='Create time'),
        ),
    ]
