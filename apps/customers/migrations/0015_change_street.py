# Generated by Django 3.1.12 on 2021-09-15 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('addresses', '0001_initial'),
        ('customers', '0014_fetch_customers_by_not_activity_sql_procedure'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""begin;
create temp table old_streets on commit drop as
select
       ls.id as locality_street_id,
       g.id as group_id,
       l.id as locality_id,
       c.baseaccount_ptr_id as customers_id
from customer_street cs
         left join groups g on cs.group_id = g.id
         left join locality l on l.title = g.title
         left join locality_street ls on l.id = ls.locality_id
         left join customers c on cs.id = c.street_id
where ls.name = cs.name;
update customers set street_id = null;
"""
        ),
        migrations.AlterField(
            model_name='customer',
            name='street',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=models.deletion.SET_NULL, to='addresses.streetmodel', verbose_name='Street'),
        ),
        migrations.AddField(
            model_name='customer',
            name='locality',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=models.deletion.SET_NULL,
                                    to='addresses.localitymodel'),
        ),
        migrations.RunSQL(
            sql="""
            update customers
set street_id = o.locality_street_id,
locality_id = o.locality_id
from (
         select os.locality_street_id, os.group_id, os.locality_id, os.customers_id
         from old_streets os
     ) as o
where customers.group_id = o.group_id
           and o.customers_id = customers.baseaccount_ptr_id;

commit;"""
        ),
        migrations.DeleteModel(
            name='CustomerStreet',
        ),
    ]
