# Generated by Django 3.2.19 on 2023-11-03 13:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0014_remove_clustergroup_sha_function'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parameter',
            name='parameter',
            field=models.CharField(choices=[('allowModsToUnmuteUsers', 'allowModsToUnmuteUsers'), ('allowStartStopRecording', 'allowStartStopRecording'), ('autoStartRecording', 'autoStartRecording'), ('bannerColor', 'bannerColor'), ('bannerText', 'bannerText'), ('copyright', 'copyright'), ('disabledFeatures', 'disabledFeatures'), ('disabledFeaturesExclude', 'disabledFeaturesExclude'), ('duration', 'duration'), ('endWhenNoModerator', 'endWhenNoModerator'), ('endWhenNoModeratorDelayInMinutes', 'endWhenNoModeratorDelayInMinutes'), ('groups', 'groups'), ('guestPolicy', 'guestPolicy'), ('learningDashboardCleanupDelayInMinutes', 'learningDashboardCleanupDelayInMinutes'), ('lockSettingsDisableCam', 'lockSettingsDisableCam'), ('lockSettingsDisableMic', 'lockSettingsDisableMic'), ('lockSettingsDisablePrivateChat', 'lockSettingsDisablePrivateChat'), ('lockSettingsDisablePublicChat', 'lockSettingsDisablePublicChat'), ('lockSettingsDisableNote', 'lockSettingsDisableNote'), ('lockSettingsHideViewersCursor', 'lockSettingsHideViewersCursor'), ('lockSettingsLockedLayout', 'lockSettingsLockedLayout'), ('lockSettingsLockOnJoin', 'lockSettingsLockOnJoin'), ('lockSettingsLockOnJoinConfigurable', 'lockSettingsLockOnJoinConfigurable'), ('logo', 'logo'), ('logoutURL', 'logoutURL'), ('maxParticipants', 'maxParticipants'), ('meetingCameraCap', 'meetingCameraCap'), ('meetingExpireIfNoUserJoinedInMinutes', 'meetingExpireIfNoUserJoinedInMinutes'), ('meetingExpireWhenLastUserLeftInMinutes', 'meetingExpireWhenLastUserLeftInMinutes'), ('meetingKeepEvents', 'meetingKeepEvents'), ('meetingLayout', 'meetingLayout'), ('meta_fullaudio-bridge', 'meta_fullaudio-bridge'), ('moderatorOnlyMessage', 'moderatorOnlyMessage'), ('muteOnStart', 'muteOnStart'), ('notifyRecordingIsOn', 'notifyRecordingIsOn'), ('preUploadedPresentation', 'preUploadedPresentation'), ('preUploadedPresentationName', 'preUploadedPresentationName'), ('preUploadedPresentationOverrideDefault', 'preUploadedPresentationOverrideDefault'), ('presentationUploadExternalUrl', 'presentationUploadExternalUrl'), ('presentationUploadExternalDescription', 'presentationUploadExternalDescription'), ('record', 'record'), ('recordFullDurationMedia', 'recordFullDurationMedia'), ('webcamsOnlyForModerator', 'webcamsOnlyForModerator'), ('welcome', 'welcome'), ('errorRedirectUrl', 'errorRedirectUrl'), ('excludeFromDashboard', 'excludeFromDashboard'), ('role', 'role'), ('userdata-bbb_ask_for_feedback_on_logout', 'userdata-bbb_ask_for_feedback_on_logout'), ('userdata-bbb_auto_join_audio', 'userdata-bbb_auto_join_audio'), ('userdata-bbb_auto_share_webcam', 'userdata-bbb_auto_share_webcam'), ('userdata-bbb_auto_swap_layout', 'userdata-bbb_auto_swap_layout'), ('userdata-bbb_client_title', 'userdata-bbb_client_title'), ('userdata-bbb_custom_style', 'userdata-bbb_custom_style'), ('userdata-bbb_custom_style_url', 'userdata-bbb_custom_style_url'), ('userdata-bbb_display_branding_area', 'userdata-bbb_display_branding_area'), ('userdata-bbb_enable_screen_sharing', 'userdata-bbb_enable_screen_sharing'), ('userdata-bbb_enable_video', 'userdata-bbb_enable_video'), ('userdata-bbb_force_restore_presentation_on_new_events', 'userdata-bbb_force_restore_presentation_on_new_events'), ('userdata-bbb_force_listen_only', 'userdata-bbb_force_listen_only'), ('userdata-bbb_fullaudio_bridge', 'userdata-bbb_fullaudio_bridge'), ('userdata-bbb_hide_presentation', 'userdata-bbb_hide_presentation'), ('userdata-bbb_hide_presentation_on_join', 'userdata-bbb_hide_presentation_on_join'), ('userdata-bbb_listen_only_mode', 'userdata-bbb_listen_only_mode'), ('userdata-bbb_mirror_own_webcam', 'userdata-bbb_mirror_own_webcam'), ('userdata-bbb_multi_user_pen_only', 'userdata-bbb_multi_user_pen_only'), ('userdata-bbb_multi_user_tools', 'userdata-bbb_multi_user_tools'), ('userdata-bbb_override_default_locale', 'userdata-bbb_override_default_locale'), ('userdata-bbb_preferred_camera_profile', 'userdata-bbb_preferred_camera_profile'), ('userdata-bbb_presenter_tools', 'userdata-bbb_presenter_tools'), ('userdata-bbb_record_video', 'userdata-bbb_record_video'), ('userdata-bbb_shortcuts', 'userdata-bbb_shortcuts'), ('userdata-bbb_show_participants_on_login', 'userdata-bbb_show_participants_on_login'), ('userdata-bbb_show_public_chat_on_login', 'userdata-bbb_show_public_chat_on_login'), ('userdata-bbb_skip_check_audio', 'userdata-bbb_skip_check_audio'), ('userdata-bbb_skip_check_audio_on_first_join', 'userdata-bbb_skip_check_audio_on_first_join'), ('userdata-bbb_skip_video_preview', 'userdata-bbb_skip_video_preview'), ('userdata-bbb_skip_video_preview_on_first_join', 'userdata-bbb_skip_video_preview_on_first_join'), ('userdata-bbb_outside_toggle_recording', 'userdata-bbb_outside_toggle_recording'), ('userdata-bbb_outside_toggle_self_voice', 'userdata-bbb_outside_toggle_self_voice')], max_length=64),
        ),
    ]
