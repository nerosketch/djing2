# Generated by Django 3.1.14 on 2022-09-30 11:16

from django.db import migrations, models
from ._funcs import prepare_sql_inject


class Migration(migrations.Migration):
    dependencies = [
        ('devices', '0010_auto_20210916_1639'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='device',
            options={
                'permissions': [
                    ('can_remove_from_olt', 'Can remove from OLT'),
                    ('can_fix_onu', 'Can fix onu'),
                    ('can_apply_onu_config', 'Can apply onu config')
                ], 'verbose_name': 'Device',
                'verbose_name_plural': 'Devices'
            },
        ),
        migrations.AlterModelOptions(
            name='port',
            options={
                'permissions': [
                    ('can_toggle_ports', 'Can toggle ports')
                ], 'verbose_name': 'Port',
                'verbose_name_plural': 'Ports'
            },
        ),
        migrations.AlterField(
            model_name='device',
            name='dev_type',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, 'Unknown Device'),
                    (2, 'PON OLT'),
                    (3, 'PON ONU BDCOM'),
                    (5, 'OLT ZTE C320'),
                    (6, 'Zte ONU F660'),
                    (7, 'Zte ONU F601'),
                    (14, 'XPON ONU FD511G'),
                    (9, 'DLink DGS-3120-24SC'),
                    (1, 'DLink DGS-1100-10/ME'),
                    (10, 'DLink DGS-1100-06/ME'),
                    (11, 'DLink DGS-3627G'),
                    (4, 'Eltex switch'),
                    (13, 'Eltex MES5324A switch'),
                    (8, 'Huawei switch'),
                    (12, 'Huawei switch S5300')
                ],
                default=0,
                verbose_name='Device type'
            ),
        ),
        migrations.RemoveField(
            model_name='device',
            name='place',
        ),
        migrations.RunSQL(sql=prepare_sql_inject()),
    ]
