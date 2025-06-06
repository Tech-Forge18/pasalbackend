# Generated by Django 5.1.7 on 2025-04-16 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('to_pay', 'To Pay'), ('to_ship', 'To Ship'), ('to_receive', 'To Receive'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('returned', 'Returned'), ('refunded', 'Refunded'), ('failed', 'Failed')], default='to_pay', max_length=20),
        ),
        migrations.AlterField(
            model_name='orderitem',
            name='status',
            field=models.CharField(choices=[('to_pay', 'To Pay'), ('to_ship', 'To Ship'), ('to_receive', 'To Receive'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('returned', 'Returned'), ('refunded', 'Refunded'), ('failed', 'Failed')], default='to_pay', max_length=20),
        ),
    ]
