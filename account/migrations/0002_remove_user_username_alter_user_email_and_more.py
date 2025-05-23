# Generated by Django 5.1.7 on 2025-05-01 05:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='username',
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='user',
            name='is_approved',
            field=models.BooleanField(default=False, help_text='Designates whether vendor account is approved.', verbose_name='approved status'),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('customer', 'Customer'), ('vendor', 'Vendor'), ('admin', 'Admin')], default='customer', max_length=20, verbose_name='role'),
        ),
    ]
