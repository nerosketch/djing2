# Generated by Django 3.0.8 on 2020-10-14 18:59

from django.db import migrations, models

from djing2.lib.for_migrations import model2default_site


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0002_alter_domain_unique"),
        ("gateways", "0002_fetch_credentials"),
    ]

    operations = [
        migrations.AddField(
            model_name="gateway",
            name="sites",
            field=models.ManyToManyField(blank=True, to="sites.Site"),
        ),
        migrations.AlterField(
            model_name="gateway",
            name="gw_type",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Mikrotik gateway"), (1, "Linux gateway")], default=0, verbose_name="Type"
            ),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: model2default_site(apps, schema_editor, "gateways", "Gateway")
        ),
    ]
