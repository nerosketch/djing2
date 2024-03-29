# Generated by Django 2.2.4 on 2020-03-13 11:58
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import netfields.fields
from djing2.lib.for_migrations import read_all_file


class Migration(migrations.Migration):

    dependencies = [
        ("groupapp", "0001_initial"),
        ("customers", "0001_initial"),
        ("networks", "0002_auto_20191218_1907"),
    ]

    operations = [
        migrations.RunSQL(
            sql=read_all_file("0003_radius_integration.sql", __file__),
            state_operations=[
                migrations.CreateModel(
                    name="CustomerIpLeaseModel",
                    fields=[
                        (
                            "id",
                            models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                        ),
                        ("ip_address", models.GenericIPAddressField(verbose_name="Ip address", unique=True)),
                        (
                            "pool",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE, to="networks.NetworkIpPool"
                            ),
                        ),
                        ("lease_time", models.DateTimeField(auto_now_add=True, verbose_name="Lease time")),
                        (
                            "mac_address",
                            netfields.fields.MACAddressField(verbose_name="Mac address", null=True, default=None),
                        ),
                        (
                            "customer",
                            models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="customers.Customer"),
                        ),
                        ("is_dynamic", models.BooleanField("Is dynamic", default=False)),
                    ],
                    options={
                        "verbose_name": "IP lease",
                        "verbose_name_plural": "IP leases",
                        "db_table": "networks_ip_leases",
                        "unique_together": {("ip_address", "mac_address", "pool", "customer")},
                    },
                ),
                migrations.CreateModel(
                    name="NetworkIpPool",
                    fields=[
                        (
                            "id",
                            models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                        ),
                        (
                            "network",
                            netfields.fields.CidrAddressField(
                                help_text="Ip address of network. For example: 192.168.1.0 or fde8:6789:1234:1::",
                                unique=True,
                                verbose_name="Ip network address",
                            ),
                        ),
                        # ('net_mask', models.PositiveSmallIntegerField(default=24, verbose_name='Network mask')),
                        (
                            "kind",
                            models.PositiveSmallIntegerField(
                                choices=[
                                    (0, "Not defined"),
                                    (1, "Internet"),
                                    (2, "Guest"),
                                    (3, "Trusted"),
                                    (4, "Devices"),
                                    (5, "Admin"),
                                ],
                                default=0,
                                verbose_name="Kind of network",
                            ),
                        ),
                        ("description", models.CharField(max_length=64, verbose_name="Description")),
                        ("ip_start", models.GenericIPAddressField(verbose_name="Start work ip range")),
                        ("ip_end", models.GenericIPAddressField(verbose_name="End work ip range")),
                        (
                            "vlan_if",
                            models.ForeignKey(
                                blank=True,
                                default=None,
                                null=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                to="networks.VlanIf",
                                verbose_name="Vlan interface",
                            ),
                        ),
                        ("gateway", models.GenericIPAddressField(verbose_name="Gateway ip address")),
                    ],
                    options={
                        "verbose_name": "Network ip pool",
                        "verbose_name_plural": "Network ip pools",
                        "db_table": "networks_ip_pool",
                        "ordering": ("network",),
                    },
                ),
                migrations.AddField(
                    model_name="networkippool",
                    name="groups",
                    field=models.ManyToManyField(
                        db_table="networks_ippool_groups",
                        to="groupapp.Group",
                        verbose_name="Member groups",
                        blank=True,
                    ),
                ),
            ],
        ),
        migrations.AlterModelOptions(
            name="vlanif",
            options={"ordering": ("-id",), "verbose_name": "Vlan", "verbose_name_plural": "Vlan list"},
        ),
        migrations.AlterField(
            model_name="vlanif",
            name="title",
            field=models.CharField(max_length=128, verbose_name="Vlan title"),
        ),
        migrations.AlterField(
            model_name="vlanif",
            name="vid",
            field=models.PositiveSmallIntegerField(
                default=1,
                unique=True,
                validators=[
                    django.core.validators.MinValueValidator(2, message="Vid could not be less then 2"),
                    django.core.validators.MaxValueValidator(4094, message="Vid could not be more than 4094"),
                ],
                verbose_name="VID",
            ),
        ),
        migrations.DeleteModel(
            name="NetworkModel",
        ),
    ]
