from django.db import migrations, models, transaction, connection
from django.db.models.deletion import CASCADE, SET_DEFAULT
from djing2.models import BaseAbstractModelMixin
import encrypted_model_fields.fields
from fin_app.models.rncb import RNCBPaymentGateway
from fin_app.models.alltime import AllTimePayGateway


def _copy_logs(apps, _):
    # Copy AllTime payment logs
    sql = """
    DO $$
    DECLARE
      log RECORD;
      new_base_log RECORD;
    BEGIN
      FOR log IN
        SELECT apl.*, bpg.id AS base_gw_id FROM all_time_pay_log apl
        LEFT JOIN pay_all_time_gateways pog ON pog.id = apl.pay_gw_id
        LEFT JOIN base_payment_gateway bpg ON (bpg.title = pog.title AND bpg.slug = pog.slug)
        ORDER BY apl.date_add
      LOOP
        INSERT INTO base_payment_log(date_add, amount, customer_id)
          VALUES (log.date_add, log.sum, log.customer_id) RETURNING id INTO new_base_log;
        INSERT INTO all_time_payment_log(basepaymentlogmodel_ptr_id, pay_id, trade_point, receipt_num, pay_gw_id)
          VALUES(new_base_log.id, log.pay_id, log.trade_point, log.receipt_num, log.base_gw_id);
      END LOOP;
    END;
    $$;
    """
    with connection.cursor() as cur:
        cur.execute(sql)

    # Copy RNCB payment logs
    sql = """
    DO $$
    DECLARE
      log RECORD;
      new_base_log RECORD;
    BEGIN
      FOR log IN
        SELECT rpl.*, bpg.id AS base_gw_id FROM rncb_pay_log rpl
        LEFT JOIN pay_rncb_gateways prg ON prg.id = rpl.pay_gw_id
        LEFT JOIN base_payment_gateway bpg ON (bpg.title = prg.title AND bpg.slug = prg.slug)
        ORDER BY rpl.date_add
      LOOP
        INSERT INTO base_payment_log(date_add, amount, customer_id)
          VALUES (log.date_add, log.amount, log.customer_id) RETURNING id INTO new_base_log;
        INSERT INTO rncb_payment_log(basepaymentlogmodel_ptr_id, pay_id, acct_time, pay_gw_id)
          VALUES(new_base_log.id, log.pay_id, log.acct_time, log.base_gw_id);
      END LOOP;
    END;
    $$;
    """
    with connection.cursor() as cur:
        cur.execute(sql)


def _copy_pay_gateways(apps, _):
    # old
    alltimepaygateway = apps.get_model('fin_app', 'PayAllTimeGateway')
    payrncbgateway = apps.get_model('fin_app', 'PayRNCBGateway')

    with transaction.atomic():
        for old_gw in alltimepaygateway.objects.order_by('id').iterator():
            g = AllTimePayGateway.objects.create(
                title=old_gw.title,
                slug=old_gw.slug,
                secret=old_gw.secret,
                service_id=old_gw.service_id,
            )
            g.sites.set((s.pk for s in old_gw.sites.all()))
            print(end='.', flush=True)

    with transaction.atomic():
        for old_gw in payrncbgateway.objects.order_by('id').iterator():
            g = RNCBPaymentGateway.objects.create(
                title=old_gw.title,
                slug=old_gw.slug,
            )
            g.sites.set((s.pk for s in old_gw.sites.all()))
            print(end='.', flush=True)


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0018_auto_20220120_1704'),
        ('sites', '0002_alter_domain_unique'),
        ('fin_app', '0003_auto_20220602_1650'),
    ]

    operations = [
        migrations.CreateModel(
            name='BasePaymentLogModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_add', models.DateTimeField(auto_now_add=True)),
                ('amount', models.DecimalField(decimal_places=6, default=0.0, max_digits=19, verbose_name='Cost')),
                ('customer', models.ForeignKey(blank=True, default=None, null=True, on_delete=SET_DEFAULT, to='customers.customer')),
            ],
            options={
                'verbose_name': 'Base payment log',
                'db_table': 'base_payment_log',
            },
            bases=(BaseAbstractModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='BasePaymentModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=64, verbose_name='Title')),
                ('slug', models.SlugField(max_length=32, verbose_name='Slug')),
                ('sites', models.ManyToManyField(blank=True, to='sites.Site')),
            ],
            options={
                'verbose_name': 'Base gateway',
                'db_table': 'base_payment_gateway',
                'unique_together': {('slug', 'title')},
            },
            bases=(BaseAbstractModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='RNCBPaymentGateway',
            fields=[
            ],
            options={
                'verbose_name': 'RNCB gateway',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('fin_app.basepaymentmodel',),
        ),
        migrations.CreateModel(
            name='AllTimePayGateway',
            fields=[
                ('basepaymentmodel_ptr', models.OneToOneField(auto_created=True, on_delete=CASCADE, parent_link=True, primary_key=True, serialize=False, to='fin_app.basepaymentmodel')),
                ('secret', encrypted_model_fields.fields.EncryptedCharField(verbose_name='Secret')),
                ('service_id', models.CharField(max_length=64, verbose_name='Service id')),
            ],
            options={
                'verbose_name': 'All time gateway',
                'db_table': 'all_time_pay_gateways',
            },
            bases=('fin_app.basepaymentmodel',),
        ),
        migrations.CreateModel(
            name='AllTimePaymentLog',
            fields=[
                ('basepaymentlogmodel_ptr', models.OneToOneField(auto_created=True, on_delete=CASCADE, parent_link=True, to='fin_app.basepaymentlogmodel')),
                ('pay_id', models.CharField(max_length=36, primary_key=True, serialize=False, unique=True)),
                ('trade_point', models.CharField(blank=True, default=None, max_length=20, null=True, verbose_name='Trade point')),
                ('receipt_num', models.BigIntegerField(default=0, verbose_name='Receipt number')),
                ('pay_gw', models.ForeignKey(on_delete=CASCADE, to='fin_app.alltimepaygateway', verbose_name='Pay gateway')),
            ],
            options={
                'db_table': 'all_time_payment_log',
            },
            bases=('fin_app.basepaymentlogmodel',),
        ),
        migrations.CreateModel(
            name='RNCBPaymentLog',
            fields=[
                ('basepaymentlogmodel_ptr', models.OneToOneField(auto_created=True, on_delete=CASCADE, parent_link=True, primary_key=True, serialize=False, to='fin_app.basepaymentlogmodel')),
                ('pay_id', models.IntegerField(unique=True)),
                ('acct_time', models.DateTimeField(verbose_name='Act time from payment system')),
            ],
            options={
                'db_table': 'rncb_payment_log',
            },
            bases=('fin_app.basepaymentlogmodel',),
        ),
        migrations.AddField(
            model_name='rncbpaymentlog',
            name='pay_gw',
            field=models.ForeignKey(on_delete=CASCADE, to='fin_app.rncbpaymentgateway', verbose_name='Pay gateway'),
        ),
        migrations.RunPython(_copy_pay_gateways),
        migrations.RunPython(_copy_logs),
        migrations.RemoveField(
            model_name='payalltimegateway',
            name='sites',
        ),
        migrations.RemoveField(
            model_name='payrncbgateway',
            name='sites',
        ),
        migrations.RemoveField(
            model_name='rncbpaylog',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='rncbpaylog',
            name='pay_gw',
        ),
        migrations.DeleteModel(
            name='AllTimePayLog',
        ),
        migrations.DeleteModel(
            name='PayAllTimeGateway',
        ),
        migrations.DeleteModel(
            name='PayRNCBGateway',
        ),
        migrations.DeleteModel(
            name='RNCBPayLog',
        ),
    ]
