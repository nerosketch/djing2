# Generated by Django 3.0.8 on 2020-10-14 18:59
from django.core.validators import MinValueValidator
from django.db import migrations, models

from djing2.lib.for_migrations import model2default_site
from services.custom_logic import periodic, oneshot, services


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0002_alter_domain_unique"),
        ("services", "0003_service_speed_burst"),
    ]

    operations = [
        migrations.AddField(
            model_name="oneshotpay",
            name="sites",
            field=models.ManyToManyField(blank=True, to="sites.Site"),
        ),
        migrations.AddField(
            model_name="periodicpay",
            name="sites",
            field=models.ManyToManyField(blank=True, to="sites.Site"),
        ),
        migrations.AddField(
            model_name="service",
            name="sites",
            field=models.ManyToManyField(blank=True, to="sites.Site"),
        ),
        migrations.AlterField(
            model_name="oneshotpay",
            name="pay_type",
            field=models.PositiveSmallIntegerField(
                choices=[(0, oneshot.ShotDefault)],
                default=0,
                help_text="Uses for callbacks before pay and after pay",
                verbose_name="One shot pay type",
            ),
        ),
        migrations.AlterField(
            model_name="periodicpay",
            name="calc_type",
            field=models.PositiveSmallIntegerField(
                choices=[(0, periodic.PeriodicPayCalcDefault), (1, periodic.PeriodicPayCalcRandom)],
                default=0,
                verbose_name="Script type for calculations",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="calc_type",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, services.ServiceDefault),
                    (1, services.TariffDp),
                    (2, services.TariffCp),
                    (3, services.TariffDaily),
                ],
                verbose_name="Script",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="cost",
            field=models.FloatField(validators=[MinValueValidator(limit_value=0.0)], verbose_name="Cost"),
        ),
        migrations.AlterField(
            model_name="service",
            name="speed_burst",
            field=models.FloatField(
                default=1.0,
                help_text="Result burst = speed * speed_burst, speed_burst must be >= 1.0",
                validators=[MinValueValidator(limit_value=1.0)],
                verbose_name="Speed burst",
            ),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: model2default_site(apps, schema_editor, "services", "Service")
        ),
        migrations.RunPython(
            lambda apps, schema_editor: model2default_site(apps, schema_editor, "services", "PeriodicPay")
        ),
        migrations.RunPython(
            lambda apps, schema_editor: model2default_site(apps, schema_editor, "services", "OneShotPay")
        ),
    ]
