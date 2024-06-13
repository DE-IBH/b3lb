# Generated by Django 3.2.23 on 2024-05-24 14:14

from django.db import migrations

def refill_record_set(apps, schema_editor):
    record_set_class = apps.get_model('rest', 'RecordSet')
    meeting_class = apps.get_model('rest', 'Meeting')
    for record_set in record_set_class.objects.all():
        if record_set.status in ["UNKNOWN", "UPLOADED"] and record_set.meta_meeting_id:
            meetings = meeting_class.objects.filter(id=record_set.meta_meeting_id, secret=record_set.secret)
            if meetings.count() == 1:
                record_set.meeting = meetings[0]
                record_set.save()

class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0020_remove_meetingold'),
    ]

    operations = [
        migrations.RunPython(refill_record_set)
    ]