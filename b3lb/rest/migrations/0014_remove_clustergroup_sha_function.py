# Generated by Django 3.2.19 on 2023-06-29 13:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0013_update_sha_and_parameters'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clustergroup',
            name='sha_function',
        ),
    ]
