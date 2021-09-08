# Generated by Django 3.1.12 on 2021-09-06 12:51

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('groupapp', '0002_group_sites'),
    ]

    operations = [
        migrations.CreateModel(
            name='FieldModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=80, verbose_name='Title')),
                ('field_type', models.PositiveSmallIntegerField(choices=[(0, 'Char Field'), (1, 'Integer Field'), (2, 'Email Field'), (3, 'Ip Field'), (4, 'Float Field'), (5, 'Slug Field')], default=0, verbose_name='Field type')),
                ('groups', models.ManyToManyField(db_table='dynamic_fields_groups', related_name='fields', to='groupapp.Group', verbose_name='Groups')),
            ],
            options={
                'db_table': 'dynamic_fields',
                'ordering': ('title',),
            },
        ),
    ]