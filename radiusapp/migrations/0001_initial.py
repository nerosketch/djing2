# Generated by Django 3.0.8 on 2020-12-10 12:52

from django.db import migrations, models
from django.db.models.deletion import CASCADE
from djing2.lib.for_migrations import read_all_file


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('customers', '0005_find_customer_service_by_device_credentials'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assign_time', models.DateTimeField(auto_now_add=True, help_text='Time when session assigned first time')),
                ('last_event_time', models.DateTimeField(verbose_name='Last update time')),
                ('radius_username', models.CharField(max_length=32, verbose_name='User-Name av pair from radius')),
                ('framed_ip_addr', models.GenericIPAddressField(verbose_name='Framed-IP-Address')),
                ('session_id', models.UUIDField(verbose_name='Unique session id')),
                ('session_duration', models.DurationField(blank=True, default=None, null=True, verbose_name='most often this is Acct-Session-Time av pair')),
                ('input_octets', models.BigIntegerField(default=0)),
                ('output_octets', models.BigIntegerField(default=0)),
                ('input_packets', models.BigIntegerField(default=0)),
                ('output_packets', models.BigIntegerField(default=0)),
                ('closed', models.BooleanField(default=False, verbose_name='Is session finished')),
                ('customer', models.ForeignKey(on_delete=CASCADE, to='customers.Customer')),
            ],
            options={
                'db_table': 'user_session',
            },
        ),
        migrations.RunSQL(
            sql=read_all_file('0001_initial.sql', __file__),
            reverse_sql="DROP FUNCTION IF EXISTS create_or_update_radius_session"
                        "( uuid, inet, macaddr, smallint, integer, varchar(32), integer, "
                        "integer, integer, integer, boolean );"
        )
    ]
