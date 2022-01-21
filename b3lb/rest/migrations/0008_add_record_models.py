# Generated by Django 3.2.10 on 2022-01-21 14:16

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import rest.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0007_alter_parameter_parameter'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='end_callback_url',
            field=models.URLField(default=''),
        ),
        migrations.AddField(
            model_name='meeting',
            name='nonce',
            field=models.CharField(default=rest.models.get_nonce, editable=False, max_length=64),
        ),
        migrations.AddField(
            model_name='secret',
            name='recording_enabled',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='secret',
            name='records_hold_time',
            field=models.IntegerField(default=14, help_text='Days interval before deleting records.', validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='tenant',
            name='recording_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tenant',
            name='records_hold_time',
            field=models.IntegerField(default=14, help_text='Days interval before deleting records.', validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='parameter',
            name='parameter',
            field=models.CharField(choices=[('allowModsToUnmuteUsers', 'allowModsToUnmuteUsers'), ('allowStartStopRecording', 'allowStartStopRecording'), ('autoStartRecording', 'autoStartRecording'), ('bannerColor', 'bannerColor'), ('bannerText', 'bannerText'), ('copyright', 'copyright'), ('duration', 'duration'), ('endWhenNoModerator', 'endWhenNoModerator'), ('endWhenNoModeratorDelayInMinutes', 'endWhenNoModeratorDelayInMinutes'), ('guestPolicy', 'guestPolicy'), ('lockSettingsDisableCam', 'lockSettingsDisableCam'), ('lockSettingsDisableMic', 'lockSettingsDisableMic'), ('lockSettingsDisablePrivateChat', 'lockSettingsDisablePrivateChat'), ('lockSettingsDisablePublicChat', 'lockSettingsDisablePublicChat'), ('lockSettingsDisableNote', 'lockSettingsDisableNote'), ('lockSettingsLockOnJoin', 'lockSettingsLockOnJoin'), ('lockSettingsLockOnJoinConfigurable', 'lockSettingsLockOnJoinConfigurable'), ('lockSettingsLockedLayout', 'lockSettingsLockedLayout'), ('logo', 'logo'), ('logoutURL', 'logoutURL'), ('maxParticipants', 'maxParticipants'), ('meetingKeepEvents', 'meetingKeepEvents'), ('moderatorOnlyMessage', 'moderatorOnlyMessage'), ('muteOnStart', 'muteOnStart'), ('webcamsOnlyForModerator', 'webcamsOnlyForModerator'), ('welcome', 'welcome'), ('meetingLayout', 'meetingLayout'), ('learningDashboardEnabled', 'learningDashboardEnabled'), ('learningDashboardCleanupDelayInMinutes', 'learningDashboardCleanupDelayInMinutes'), ('role', 'role'), ('excludeFromDashboard', 'excludeFromDashboard'), ('userdata-bbb_ask_for_feedback_on_logout', 'userdata-bbb_ask_for_feedback_on_logout'), ('userdata-bbb_auto_join_audio', 'userdata-bbb_auto_join_audio'), ('userdata-bbb_client_title', 'userdata-bbb_client_title'), ('userdata-bbb_force_listen_only', 'userdata-bbb_force_listen_only'), ('userdata-bbb_listen_only_mode', 'userdata-bbb_listen_only_mode'), ('userdata-bbb_skip_check_audio', 'userdata-bbb_skip_check_audio'), ('userdata-bbb_skip_check_audio_on_first_join', 'userdata-bbb_skip_check_audio_on_first_join'), ('userdata-bbb_override_default_locale', 'userdata-bbb_override_default_locale'), ('userdata-bbb_display_branding_area', 'userdata-bbb_display_branding_area'), ('userdata-bbb_shortcuts', 'userdata-bbb_shortcuts'), ('userdata-bbb_auto_share_webcam', 'userdata-bbb_auto_share_webcam'), ('userdata-bbb_preferred_camera_profile', 'userdata-bbb_preferred_camera_profile'), ('userdata-bbb_enable_screen_sharing', 'userdata-bbb_enable_screen_sharing'), ('userdata-bbb_enable_video', 'userdata-bbb_enable_video'), ('userdata-bbb_record_video', 'userdata-bbb_record_video'), ('userdata-bbb_skip_video_preview', 'userdata-bbb_skip_video_preview'), ('userdata-bbb_skip_video_preview_on_first_join', 'userdata-bbb_skip_video_preview_on_first_join'), ('userdata-bbb_mirror_own_webcam', 'userdata-bbb_mirror_own_webcam'), ('userdata-bbb_force_restore_presentation_on_new_events', 'userdata-bbb_force_restore_presentation_on_new_events'), ('userdata-bbb_multi_user_pen_only', 'userdata-bbb_multi_user_pen_only'), ('userdata-bbb_presenter_tools', 'userdata-bbb_presenter_tools'), ('userdata-bbb_multi_user_tools', 'userdata-bbb_multi_user_tools'), ('userdata-bbb_custom_style', 'userdata-bbb_custom_style'), ('userdata-bbb_custom_style_url', 'userdata-bbb_custom_style_url'), ('userdata-bbb_auto_swap_layout', 'userdata-bbb_auto_swap_layout'), ('userdata-bbb_hide_presentation', 'userdata-bbb_hide_presentation'), ('userdata-bbb_show_participants_on_login', 'userdata-bbb_show_participants_on_login'), ('userdata-bbb_show_public_chat_on_login', 'userdata-bbb_show_public_chat_on_login'), ('userdata-bbb_outside_toggle_self_voice', 'userdata-bbb_outside_toggle_self_voice'), ('userdata-bbb_outside_toggle_recording', 'userdata-bbb_outside_toggle_recording')], max_length=64),
        ),
        migrations.CreateModel(
            name='RecordSet',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('recording_ready_origin_url', models.URLField(default='')),
                ('nonce', models.CharField(default=rest.models.get_nonce, editable=False, max_length=64)),
                ('meeting', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='rest.meeting')),
                ('secret', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.secret')),
            ],
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('id', models.CharField(max_length=100)),
                ('storage_id', models.CharField(default='', max_length=100)),
                ('duration', models.IntegerField(default=0)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('relation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rest.recordset')),
            ],
        ),
    ]
