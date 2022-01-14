# Generated by Django 3.2.15 on 2022-08-08 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0008_alter_tenant_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parameter',
            name='parameter',
            field=models.CharField(choices=[('allowModsToUnmuteUsers', 'allowModsToUnmuteUsers'), ('bannerColor', 'bannerColor'), ('bannerText', 'bannerText'), ('copyright', 'copyright'), ('disabledFeatures', 'disabledFeatures'), ('duration', 'duration'), ('endWhenNoModerator', 'endWhenNoModerator'), ('endWhenNoModeratorDelayInMinutes', 'endWhenNoModeratorDelayInMinutes'), ('groups', 'groups'), ('guestPolicy', 'guestPolicy'), ('lockSettingsDisableCam', 'lockSettingsDisableCam'), ('lockSettingsDisableMic', 'lockSettingsDisableMic'), ('lockSettingsDisablePrivateChat', 'lockSettingsDisablePrivateChat'), ('lockSettingsDisablePublicChat', 'lockSettingsDisablePublicChat'), ('lockSettingsDisableNote', 'lockSettingsDisableNote'), ('lockSettingsHideViewersCursor', 'lockSettingsHideViewersCursor'), ('lockSettingsLockOnJoin', 'lockSettingsLockOnJoin'), ('lockSettingsLockOnJoinConfigurable', 'lockSettingsLockOnJoinConfigurable'), ('lockSettingsLockedLayout', 'lockSettingsLockedLayout'), ('logo', 'logo'), ('logoutURL', 'logoutURL'), ('maxParticipants', 'maxParticipants'), ('meetingCameraCap', 'meetingCameraCap'), ('meetingExpireIfNoUserJoinedInMinutes', 'meetingExpireIfNoUserJoinedInMinutes'), ('meetingExpireWhenLastUserLeftInMinutes', 'meetingExpireWhenLastUserLeftInMinutes'), ('meetingKeepEvents', 'meetingKeepEvents'), ('moderatorOnlyMessage', 'moderatorOnlyMessage'), ('muteOnStart', 'muteOnStart'), ('webcamsOnlyForModerator', 'webcamsOnlyForModerator'), ('welcome', 'welcome'), ('meetingLayout', 'meetingLayout'), ('preUploadedPresentationOverrideDefault', 'preUploadedPresentationOverrideDefault'), ('learningDashboardCleanupDelayInMinutes', 'learningDashboardCleanupDelayInMinutes'), ('role', 'role'), ('excludeFromDashboard', 'excludeFromDashboard'), ('userdata-bbb_ask_for_feedback_on_logout', 'userdata-bbb_ask_for_feedback_on_logout'), ('userdata-bbb_auto_join_audio', 'userdata-bbb_auto_join_audio'), ('userdata-bbb_client_title', 'userdata-bbb_client_title'), ('userdata-bbb_force_listen_only', 'userdata-bbb_force_listen_only'), ('userdata-bbb_listen_only_mode', 'userdata-bbb_listen_only_mode'), ('userdata-bbb_skip_check_audio', 'userdata-bbb_skip_check_audio'), ('userdata-bbb_skip_check_audio_on_first_join', 'userdata-bbb_skip_check_audio_on_first_join'), ('userdata-bbb_override_default_locale', 'userdata-bbb_override_default_locale'), ('userdata-bbb_display_branding_area', 'userdata-bbb_display_branding_area'), ('userdata-bbb_shortcuts', 'userdata-bbb_shortcuts'), ('userdata-bbb_auto_share_webcam', 'userdata-bbb_auto_share_webcam'), ('userdata-bbb_preferred_camera_profile', 'userdata-bbb_preferred_camera_profile'), ('userdata-bbb_enable_screen_sharing', 'userdata-bbb_enable_screen_sharing'), ('userdata-bbb_enable_video', 'userdata-bbb_enable_video'), ('userdata-bbb_record_video', 'userdata-bbb_record_video'), ('userdata-bbb_skip_video_preview', 'userdata-bbb_skip_video_preview'), ('userdata-bbb_skip_video_preview_on_first_join', 'userdata-bbb_skip_video_preview_on_first_join'), ('userdata-bbb_mirror_own_webcam', 'userdata-bbb_mirror_own_webcam'), ('userdata-bbb_force_restore_presentation_on_new_events', 'userdata-bbb_force_restore_presentation_on_new_events'), ('userdata-bbb_multi_user_pen_only', 'userdata-bbb_multi_user_pen_only'), ('userdata-bbb_presenter_tools', 'userdata-bbb_presenter_tools'), ('userdata-bbb_multi_user_tools', 'userdata-bbb_multi_user_tools'), ('userdata-bbb_custom_style', 'userdata-bbb_custom_style'), ('userdata-bbb_custom_style_url', 'userdata-bbb_custom_style_url'), ('userdata-bbb_auto_swap_layout', 'userdata-bbb_auto_swap_layout'), ('userdata-bbb_hide_presentation', 'userdata-bbb_hide_presentation'), ('userdata-bbb_show_participants_on_login', 'userdata-bbb_show_participants_on_login'), ('userdata-bbb_show_public_chat_on_login', 'userdata-bbb_show_public_chat_on_login'), ('userdata-bbb_outside_toggle_self_voice', 'userdata-bbb_outside_toggle_self_voice'), ('userdata-bbb_outside_toggle_recording', 'userdata-bbb_outside_toggle_recording')], max_length=64),
        ),
    ]