# Generated by Django 3.1.14 on 2022-05-26 13:47

from django.db import migrations
import dynamicfields.models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0018_auto_20220120_1704'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerdynamicfieldcontentmodel',
            name='content',
            field=dynamicfields.models.DynamicField(blank=True, null=True),
        ),
    ]
