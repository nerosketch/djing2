# Generated by Django 3.0.7 on 2020-07-07 11:02

from django.db import migrations
from djing2.lib.for_migrations import read_all_file


class Migration(migrations.Migration):

    dependencies = [
        ("networks", "0006_change_fetch_subscriber_lease"),
    ]

    operations = [migrations.RunSQL(sql=read_all_file("0007_signal_from_external_dhcp.sql", __file__))]
