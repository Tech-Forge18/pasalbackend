# Generated by Django 5.1.7 on 2025-05-02 04:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_remove_user_username_alter_user_email_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='account_use_email_553b8f_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['role'], name='account_use_role_f4255b_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['is_approved'], name='account_use_is_appr_710442_idx'),
        ),
    ]
