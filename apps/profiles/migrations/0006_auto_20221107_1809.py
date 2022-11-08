# Generated by Django 3.1.14 on 2022-11-07 18:09

from django.db import migrations, models
import profiles.models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_auto_20210204_2043'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='baseaccount',
            options={},
        ),
        migrations.AlterModelOptions(
            name='profileauthlog',
            options={},
        ),
        migrations.AlterModelOptions(
            name='userprofile',
            options={'verbose_name': 'Staff account profile', 'verbose_name_plural': 'Staff account profiles'},
        ),
        migrations.AlterModelOptions(
            name='userprofilelog',
            options={'verbose_name': 'User profile log', 'verbose_name_plural': 'User profile logs'},
        ),
        migrations.AlterField(
            model_name='baseaccount',
            name='birth_day',
            field=models.DateField(blank=True, default=None, null=True, validators=[profiles.models.birth_day_18yo_validator, profiles.models.birth_day_too_old_validator], verbose_name='birth day'),
        ),
        migrations.AlterField(
            model_name='baseaccount',
            name='is_active',
            field=models.BooleanField(default=False, verbose_name='Is active'),
        ),
    ]
