from django.db import migrations, models, transaction
from django.db.models.deletion import CASCADE, SET_DEFAULT
from djing2.models import BaseAbstractModelMixin
import encrypted_model_fields.fields
from fin_app.models.rncb import RNCBPaymentGateway, RNCBPaymentLog
from fin_app.models.alltime import AllTimePaymentLog, AllTimePayGateway


def _copy_logs(apps, _):
    alltimepaylog = apps.get_model('fin_app', 'AllTimePayLog')
    rncbpaylog = apps.get_model('fin_app', 'RNCBPayLog')

    with transaction.atomic():
        for old_log in rncbpaylog.objects.iterator():
            RNCBPaymentLog.objects.create(
                customer_id=old_log.customer_id,
                date_add=old_log.date_add,
                amount=old_log.amount,
                pay_id=old_log.pay_id,
                acct_time=old_log.acct_time,
                pay_gw_id=old_log.pay_gw_id,
            )

    with transaction.atomic():
        for old_log in alltimepaylog.objects.iterator():
            AllTimePaymentLog.objects.create(
                customer_id=old_log.customer_id,
                date_add=old_log.date_add,
                amount=old_log.sum,
                pay_id=old_log.pay_id,
                trade_point=old_log.trade_point,
                receipt_num=old_log.receipt_num,
                pay_gw_id=old_log.pay_gw_id,
            )


def _copy_pay_gateways(apps, _):
    # old
    alltimepaygateway = apps.get_model('fin_app', 'PayAllTimeGateway')
    payrncbgateway = apps.get_model('fin_app', 'PayRNCBGateway')

    assert alltimepaygateway.objects.count() > 0
    assert payrncbgateway.objects.count() > 0

    for old_gw in alltimepaygateway.objects.iterator():
        g = AllTimePayGateway.objects.create(
            title=old_gw.title,
            slug=old_gw.slug,
            secret=old_gw.secret,
            service_id=old_gw.service_id,
        )
        g.sites.set((s.pk for s in old_gw.sites.all()))
        print(end='.', flush=True)

    for old_gw in payrncbgateway.objects.iterator():
        g = RNCBPaymentGateway.objects.create(
            title=old_gw.title,
            slug=old_gw.slug,
            secret=old_gw.secret,
            service_id=old_gw.service_id,
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
                ('slug', models.SlugField(max_length=32, unique=True, verbose_name='Slug')),
                ('sites', models.ManyToManyField(blank=True, to='sites.Site')),
            ],
            options={
                'verbose_name': 'Base gateway',
                'db_table': 'base_payment_gateway',
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
