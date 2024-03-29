# Generated by Django 3.1.7 on 2021-06-09 15:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groupapp', '0002_group_sites'),
        ('sorm_export', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fiasrecursiveaddressmodel',
            name='groups'
        ),
        migrations.AddField(
            model_name='fiasrecursiveaddressmodel',
            name='groups',
            field=models.ManyToManyField(to='groupapp.Group', blank=True)
        ),
        migrations.DeleteModel(
            name='FiasAddrGroupModel',
        ),
        migrations.AlterField(
            model_name='exportstampmodel',
            name='data',
            field=models.JSONField(verbose_name='Export event data'),
        ),
        migrations.RunSQL(
            sql="""
ALTER TABLE IF EXISTS sorm_address_groups DROP CONSTRAINT if exists sorm_address_groups_groupsid_uniq;
DROP VIEW IF EXISTS get_streets_as_addr_objects;
            """
        ),
    ]
