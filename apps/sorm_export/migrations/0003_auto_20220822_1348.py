# Generated by Django 3.1.14 on 2022-08-22 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sorm_export', '0002_auto_20210609_1511'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exportstampmodel',
            name='data',
            field=models.JSONField(blank=True, default=None, null=True, verbose_name='Export event data'),
        ),
        migrations.AlterField(
            model_name='exportstampmodel',
            name='export_type',
            field=models.IntegerField(choices=[(0, 'Unknown Choice'), (1, 'Customer Root'), (2, 'Customer Contract'), (3, 'Customer Address'), (4, 'Customer Ap Address'), (5, 'Customer Individual'), (6, 'Customer Legal'), (7, 'Customer Contact'), (8, 'Network Static Ip'), (9, 'Payment Unknown'), (10, 'Service Nomenclature'), (11, 'Service Customer'), (12, 'Service Customer Manual'), (13, 'Device Switch'), (14, 'Ip Numbering'), (15, 'Gateways')], default=0, verbose_name='Export type'),
        ),
    ]