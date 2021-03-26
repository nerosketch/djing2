# Generated by Django 3.0.8 on 2020-11-05 14:20

from django.db import migrations, models
from djing2.lib.for_migrations import read_all_file


class Migration(migrations.Migration):

    dependencies = [
        ('networks', '0007_signal_from_external_dhcp'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='customeripleasemodel',
            options={'ordering': ('id',), 'verbose_name': 'IP lease', 'verbose_name_plural': 'IP leases'},
        ),
        migrations.AlterModelOptions(
            name='vlanif',
            options={'ordering': ('vid',), 'verbose_name': 'Vlan', 'verbose_name_plural': 'Vlan list'},
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='last_update',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='Last update'),
        ),
        migrations.RunSQL(
            sql=read_all_file('0008_update_lease_last_update_time.sql', __file__)
        ),
    ]