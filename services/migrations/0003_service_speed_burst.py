# Generated by Django 2.2.10 on 2020-03-22 00:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_oneshotpay'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='speed_burst',
            field=models.FloatField(default=1.0, help_text='Result burst = speed * speed_burst, speed_burst must be > 1.0', verbose_name='Speed burst'),
        ),
    ]
