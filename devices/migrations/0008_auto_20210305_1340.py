# Generated by Django 3.1.7 on 2021-03-05 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0007_device_sites"),
    ]

    operations = [
        migrations.AlterField(
            model_name="device",
            name="dev_type",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Unknown Device"),
                    (1, "DLink DGS-1100-10/ME"),
                    (2, "PON OLT"),
                    (3, "PON ONU BDCOM"),
                    (4, "Eltex switch"),
                    (5, "OLT ZTE C320"),
                    (6, "Zte ONU F660"),
                    (7, "Zte ONU F601"),
                    (8, "Huawei switch"),
                    (9, "DLink DGS-3120-24SC"),
                    (10, "DLink DGS-1100-06/ME"),
                    (11, "DLink DGS-3627G"),
                    (12, "Huawei switch"),
                ],
                default=0,
                verbose_name="Device type",
            ),
        ),
        migrations.AlterField(
            model_name="device",
            name="extra_data",
            field=models.JSONField(
                blank=True,
                help_text="Extra data in JSON format. You may use it for your custom data",
                null=True,
                verbose_name="Extra data",
            ),
        ),
        migrations.RunSQL(sql="UPDATE device_dev_type_is_use_dev_port SET is_use_dev_port=true WHERE dev_type=12"),
    ]
