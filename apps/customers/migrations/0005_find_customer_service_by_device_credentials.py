# Generated by Django 3.0.8 on 2020-12-03 13:52

from django.db import migrations

from djing2.lib.for_migrations import read_all_file


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0004_auto_20201014_1859"),
    ]

    operations = [
        migrations.RunSQL(
            sql=read_all_file("0005_find_customer_service_by_device_credentials.sql", __file__),
            reverse_sql="DROP FUNCTION IF EXISTS find_customer_service_by_device_credentials( macaddr, smallint );",
        )
    ]
