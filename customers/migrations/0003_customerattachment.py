# Generated by Django 2.2 on 2020-06-08 16:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial'),
        ('customers', '0002_add_procedures'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerAttachment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=64)),
                ('doc_file', models.FileField(max_length=128, upload_to='customer_attachments/%Y/%m/')),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.UserProfile')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customers.Customer')),
            ],
            options={
                'db_table': 'customer_attachments',
            },
        ),
    ]
