# Generated by Django 3.0.8 on 2021-03-01 17:29

from django.db import migrations

from djing2.lib.for_migrations import read_all_file


class Migration(migrations.Migration):

    dependencies = [
        ('networks', '0012_customeripleaselog'),
    ]

    operations = [
        migrations.RunSQL(
            sql=read_all_file('0013_update_dhcp_commit_lease_add_update_fn.sql', __file__)
        )
    ]
