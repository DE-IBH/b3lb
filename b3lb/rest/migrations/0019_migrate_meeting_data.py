# Generated by Django 3.2.23 on 2024-05-24 13:29

from django.db import migrations

def migrate_meetings(apps, schema_editor):
    meeting_class = apps.get_model("rest", "MeetingNew")
    meeting_old_class = apps.get_model("rest", "MeetingOld")
    for meeting_old in meeting_old_class.objects.all():
        meeting = meeting_class()
        meeting.id = meeting_old.id
        meeting.secret = meeting_old.secret
        meeting.node = meeting_old.node
        meeting.room_name = meeting_old.room_name
        meeting.age = meeting_old.age
        meeting.attendees = meeting_old.attendees
        meeting.end_callback_url = meeting_old.end_callback_url
        meeting.listenerCount = meeting_old.listenerCount
        meeting.nonce = meeting_old.nonce
        meeting.voiceParticipantCount = meeting_old.voiceParticipantCount
        meeting.moderatorCount = meeting_old.moderatorCount
        meeting.videoCount = meeting_old.videoCount
        meeting.bbb_origin = meeting_old.bbb_origin
        meeting.bbb_origin_server_name = meeting_old.bbb_origin_server_name
        meeting.save()


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0018_meeting'),
    ]

    operations = [
        migrations.RunPython(migrate_meetings)
    ]