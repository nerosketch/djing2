# Generated by Django 3.1.14 on 2022-08-04 12:03

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
        migrations.AlterUniqueTogether(
            name='additionaltelephone',
            unique_together={('customer', 'telephone')},
        ),
    ]
