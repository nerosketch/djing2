# Generated by Django 2.2.9 on 2020-04-25 14:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("networks", "0003_radius_integration"),
    ]

    operations = [
        migrations.AddField(
            model_name="networkippool",
            name="is_dynamic",
            field=models.BooleanField(default=False, verbose_name="Is dynamic"),
        )
    ]
