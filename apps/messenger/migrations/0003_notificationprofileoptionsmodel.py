# Generated by Django 3.1.12 on 2021-09-19 23:56

import bitfield.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_auto_20210204_2043'),
        ('messenger', '0002_auto_20210716_2137'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationProfileOptionsModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_flags', bitfield.models.BitField((('telegram', 'Telegram notifications'), ('viber', 'Viber notifications'), ('email', 'Email notifications'), ('push', 'Push notifications'), ('custom', 'Custom notifications')), default=0)),
                ('various_options', models.JSONField()),
                ('profile', models.OneToOneField(on_delete=models.deletion.CASCADE, to='profiles.userprofile')),
            ],
            options={
                'db_table': 'messenger_options',
            },
        ),
    ]
