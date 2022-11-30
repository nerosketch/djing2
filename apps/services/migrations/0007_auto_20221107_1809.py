# Generated by Django 3.1.14 on 2022-11-07 18:09

from datetime import timedelta
import django.core.validators
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion
import djing2.models


def update_deadlines(apps, schema_editor):
    customer_service_model = apps.get_model('services', 'CustomerService')
    customer_service_model.objects.filter(
        deadline__hour=23,
        deadline__minute=59,
        deadline__second=59,
    ).update(deadline=models.F('deadline') + timedelta(seconds=1))


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0019_auto_20220804_1203'),
        ('services', '0006_auto_20210305_1316'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='oneshotpay',
            options={},
        ),
        migrations.AlterModelOptions(
            name='periodicpay',
            options={'verbose_name': 'Periodic pay', 'verbose_name_plural': 'Periodic pays'},
        ),
        migrations.AlterModelOptions(
            name='service',
            options={'verbose_name': 'Service', 'verbose_name_plural': 'Services'},
        ),
        migrations.AlterField(
            model_name='service',
            name='cost',
            field=models.DecimalField(decimal_places=2, max_digits=7, validators=[django.core.validators.MinValueValidator(limit_value=0.0)], verbose_name='Cost'),
        ),
        migrations.CreateModel(
            name='CustomerServiceConnectingQueueModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number_queue', models.IntegerField(verbose_name='Number in the queue', db_index=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_queue', to='customers.Customer')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_service_queue', to='services.service')),
            ],
            options={
                'db_table': 'services_queue',
                'constraints': [
                    models.UniqueConstraint(
                        deferrable=django.db.models.constraints.Deferrable['DEFERRED'],
                        fields=('customer', 'number_queue'),
                        name='customer_number_queue_unique'
                    )
                ]
            },
        ),
        migrations.RunSQL(
            sql="INSERT INTO services_queue(customer_id, service_id, number_queue) SELECT c.baseaccount_ptr_id, c.last_connected_service_id, 1 FROM customers c WHERE c.last_connected_service_id IS NOT NULL"
        ),
        migrations.RunSQL(
            sql="DROP FUNCTION find_customer_service_by_device_credentials( integer, integer )"
        ),
        migrations.RunSQL(
            sql=(
                'CREATE TABLE customer_service_tmp (id serial NOT NULL PRIMARY KEY, customer_id integer NOT NULL UNIQUE, start_time timestamp with time zone NULL, deadline timestamp with time zone NULL, service_id integer NOT NULL, cost double precision not null);\n',
                'INSERT INTO customer_service_tmp(start_time, deadline, service_id, customer_id, cost) SELECT cs.start_time, cs.deadline, cs.service_id, c.baseaccount_ptr_id, s.cost FROM customer_service cs RIGHT JOIN customers c ON c.current_service_id = cs.id LEFT JOIN services s on cs.service_id = s.id WHERE CS.id IS NOT NULL;\n'
                'DROP TABLE customer_service CASCADE;\n'
                'ALTER TABLE customer_service_tmp RENAME TO customer_service;\n'
                'ALTER TABLE "customer_service" ADD CONSTRAINT "customer_service_customer_id_service_id_08d6f028_uniq" UNIQUE ("customer_id", "service_id");\n'
                'ALTER TABLE "customer_service" ADD CONSTRAINT "customer_service_service_id_bd5f1ba6_fk_services_id" FOREIGN KEY ("service_id") REFERENCES "services" ("id") DEFERRABLE INITIALLY DEFERRED;\n'
                'ALTER TABLE "customer_service" ADD CONSTRAINT "customer_service_customer_id_30a14af1_fk_customers" FOREIGN KEY ("customer_id") REFERENCES "customers" ("baseaccount_ptr_id") DEFERRABLE INITIALLY DEFERRED;\n'
                'CREATE INDEX "customer_service_service_id_bd5f1ba6" ON "customer_service" ("service_id")'
            ),
            state_operations=[
                migrations.CreateModel(
                    name='CustomerService',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('customer', models.OneToOneField(
                            on_delete=django.db.models.deletion.CASCADE,
                            related_name='current_service', to='customers.customer'
                        )),
                        ('start_time', models.DateTimeField(blank=True, default=None, null=True)),
                        ('deadline', models.DateTimeField(blank=True, default=None, null=True)),
                        ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='link_to_service', to='services.service')),
                        ('cost', models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(limit_value=0.0)])),
                    ],
                    options={
                        'verbose_name': 'Customer service',
                        'verbose_name_plural': 'Customer services',
                        'db_table': 'customer_service',
                        'permissions': [('can_view_service_type_report', 'Can view service type report'), ('can_view_activity_report', 'Can view activity_report')],
                        'unique_together': {('customer', 'service')},
                    },
                    bases=(djing2.models.BaseAbstractModelMixin, models.Model),
                )
            ]
        ),
        # move deadlines to one sec forward
        migrations.RunPython(update_deadlines),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='PeriodicPayForId',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('last_pay', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Last pay time')),
                        ('next_pay', models.DateTimeField(verbose_name='Next time to pay')),
                        ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers.customer', verbose_name='Account')),
                        ('periodic_pay', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.periodicpay', verbose_name='Periodic pay')),
                    ],
                    options={
                        'db_table': 'periodic_pay_for_id',
                    },
                    bases=(djing2.models.BaseAbstractModelMixin, models.Model),
                ),
            ]
        )
    ]
