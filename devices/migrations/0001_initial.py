# Generated by Django 2.2.3 on 2019-07-19 00:25

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import macaddress.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('groupapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='Ip address')),
                ('mac_addr', macaddress.fields.MACAddressField(blank=True, unique=True, integer=True, null=True, verbose_name='Mac address')),
                ('comment', models.CharField(max_length=256, verbose_name='Comment')),
                ('dev_type', models.PositiveSmallIntegerField(choices=[(1, 'DLink switch'), (2, 'PON OLT'), (3, 'PON ONU BDCOM'), (4, 'Eltex switch'), (5, 'OLT ZTE C320'), (6, 'Zte ONU F660'), (7, 'Zte ONU F601'), (8, 'Huawei switch')], default=1, verbose_name='Device type')),
                ('man_passw', models.CharField(blank=True, max_length=16, null=True, verbose_name='SNMP password')),
                ('snmp_extra', models.CharField(blank=True, max_length=256, null=True, verbose_name='SNMP extra info')),
                ('extra_data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, help_text='Extra data in JSON format. You may use it for your custom data', null=True, verbose_name='Extra data')),
                ('status', models.PositiveSmallIntegerField(choices=[(0, 'Undefined'), (1, 'Up'), (2, 'Unreachable'), (3, 'Down')], default=0, verbose_name='Status')),
                ('is_noticeable', models.BooleanField(default=False, verbose_name='Send notify when monitoring state changed')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='groupapp.Group', verbose_name='Device group')),
                ('parent_dev', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='devices.Device', verbose_name='Parent device')),
            ],
            options={
                'verbose_name': 'Device',
                'verbose_name_plural': 'Devices',
                'db_table': 'device',
                'ordering': ('id',),
            },
        ),
        migrations.CreateModel(
            name='Port',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('num', models.PositiveSmallIntegerField(default=0, verbose_name='Number')),
                ('descr', models.CharField(blank=True, max_length=60, null=True, verbose_name='Description')),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='devices.Device', verbose_name='Device')),
            ],
            options={
                'verbose_name': 'Port',
                'verbose_name_plural': 'Ports',
                'db_table': 'device_port',
                'ordering': ('num',),
                'permissions': (('can_toggle_ports', 'Can toggle ports'),),
                'unique_together': {('device', 'num')},
            },
        ),
    ]
