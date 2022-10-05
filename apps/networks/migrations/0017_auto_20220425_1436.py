# Generated by Django 3.1.14 on 2022-04-25 14:36

from django.db import migrations, models
from djing2.lib.for_migrations import read_all_file


copy_from_old_sessions_sql = (
    "UPDATE networks_ip_leases AS l SET input_octets=0, output_octets=0, input_packets=0, output_packets=0,"
    "session_id=s.session_id FROM radius_customer_session AS s WHERE s.ip_lease_id = l.id;"
)


class Migration(migrations.Migration):

    dependencies = [
        ('networks', '0016_auto_20220117_1027'),
        ('radiusapp', '0003_auto_20220106_1622'),
    ]

    operations = [
        migrations.AddField(
            model_name='customeripleasemodel',
            name='cvid',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Customer Vlan id'),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='input_octets',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='input_packets',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='output_octets',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='output_packets',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='radius_username',
            field=models.CharField(blank=True, default=None, max_length=128, null=True, verbose_name='User-Name av pair from radius'),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='session_id',
            field=models.UUIDField(blank=True, default=None, null=True, verbose_name='Unique session id'),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='state',
            field=models.BooleanField(blank=True, default=None, null=True, verbose_name='Lease state'),
        ),
        migrations.AddField(
            model_name='customeripleasemodel',
            name='svid',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Service Vlan id'),
        ),
        migrations.AlterUniqueTogether(
            name='customeripleasemodel',
            unique_together=set(),
        ),
        migrations.RunSQL(sql=copy_from_old_sessions_sql),
        migrations.RunSQL(sql=read_all_file("0017_auto_20220425_1436.sql", __file__)),
    ]

