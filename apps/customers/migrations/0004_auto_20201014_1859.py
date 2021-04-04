# Generated by Django 3.0.8 on 2020-10-14 18:59

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0003_customerattachment"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="customer",
            options={
                "ordering": ("fio",),
                "permissions": [
                    ("can_buy_service", "Buy service perm"),
                    ("can_add_balance", "fill account"),
                    ("can_ping", "Can ping"),
                    ("can_complete_service", "Can complete service"),
                ],
                "verbose_name": "Customer",
                "verbose_name_plural": "Customers",
            },
        ),
        migrations.AlterModelOptions(
            name="customerattachment",
            options={"ordering": ("id",)},
        ),
        migrations.AlterModelOptions(
            name="customerservice",
            options={
                "ordering": ("start_time",),
                "verbose_name": "Customer service",
                "verbose_name_plural": "Customer services",
            },
        ),
        migrations.AlterModelOptions(
            name="customerstreet",
            options={"ordering": ("name",), "verbose_name": "Street", "verbose_name_plural": "Streets"},
        ),
    ]
