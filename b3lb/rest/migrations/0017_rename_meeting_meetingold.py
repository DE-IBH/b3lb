# Generated by Django 3.2.23 on 2024-05-24 13:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0016_resize_meeting_name_length'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Meeting',
            new_name='MeetingOld',
        ),
    ]
