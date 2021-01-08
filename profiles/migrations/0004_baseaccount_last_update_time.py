# Generated by Django 3.0.8 on 2021-01-08 16:32

from django.db import migrations, models
from djing2.lib.for_migrations import read_all_file


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_baseaccount_sites'),
    ]

    operations = [
        migrations.AddField(
            model_name='baseaccount',
            name='last_update_time',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='Last update time'),
        ),
        migrations.RunSQL(
            sql=read_all_file('0004_baseaccount_last_update_time_trigger.sql', __file__),
        )
    ]
