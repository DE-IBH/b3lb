# Regexes

from rest.parameters.create import *
from rest.parameters.join import *

BOOLEAN_REGEX = r'^(true|false)$'
NUMBER_REGEX = r'^\d+$'
POLICY_REGEX = r'^(ALWAYS_ACCEPT|ALWAYS_DENY|ASK_MODERATOR)$'
COLOR_REGEX = r'^#[a-fA-F0-9]{6}$'
LOCALE_REGEX = r'^[a-z]{2}$'
CAMERA_REGEX = r'^(low-u30|low-u25|low-u20|low-u15|low-u12|low-u8|low|medium|high|hd)$'
URL_REGEX = r"^https?://[\w.-]+(?:\.[\w.-]+)+[\w._~:/?#[\]@!\$&'()*+,;=.%-]+$"
ROLE_REGEX = r'^(VIEWER|MODERATOR)$'
MEETING_LAYOUT_REGEX = r'(CUSTOM_LAYOUT|SMART_LAYOUT|PRESENTATION_FOCUS|VIDEO_FOCUS|CAMERAS_ONLY|PARTICIPANTS_CHAT_ONLY|PRESENTATION_ONLY|MEDIA_ONLY)$'
AUDIO_BRIDGE_REGEX = r'^(sipjs|kurento|fullaudio)$'
ANY_REGEX = r'.'


PARAMETER_REGEXES = {
    # Create
    ALLOW_MODS_TO_UNMUTE_USERS: BOOLEAN_REGEX,
    ALLOW_OVERRIDE_CLIENT_SETTING_ON_CREATE_CALL: BOOLEAN_REGEX,
    ALLOW_PROMOTE_GUEST_TO_MODERATOR: BOOLEAN_REGEX,
    ALLOW_START_STOP_RECORDING: BOOLEAN_REGEX,
    AUTO_START_RECORDING: BOOLEAN_REGEX,
    BANNER_COLOR: COLOR_REGEX,
    BANNER_TEXT: ANY_REGEX,
    CLIENT_SETTINGS_OVERRIDE: ANY_REGEX,
    COPYRIGHT: ANY_REGEX,
    DISABLED_FEATURES: ANY_REGEX,
    DISABLED_FEATURES_EXCLUDED: ANY_REGEX,
    DURATION: NUMBER_REGEX,
    END_WHEN_NO_MODERATOR: BOOLEAN_REGEX,
    END_WHEN_NO_MODERATOR_DELAY_IN_MINUTES: NUMBER_REGEX,
    FIRST_NAME: ANY_REGEX,
    GROUPS: ANY_REGEX,
    GUEST_POLICY: POLICY_REGEX,
    LAST_NAME: ANY_REGEX,
    LEARNING_DASHBOARD_CLEANUP_DELAY_IN_MINUTES: NUMBER_REGEX,
    LOCK_SETTINGS_DISABLE_CAM: BOOLEAN_REGEX,
    LOCK_SETTINGS_DISABLE_MIC: BOOLEAN_REGEX,
    LOCK_SETTINGS_DISABLE_PRIVATE_CHAT: BOOLEAN_REGEX,
    LOCK_SETTINGS_DISABLE_PUBLIC_CHAT: BOOLEAN_REGEX,
    LOCK_SETTINGS_DISABLE_NOTE: BOOLEAN_REGEX,
    LOCK_SETTINGS_HIDE_VIEWER_CURSOR: BOOLEAN_REGEX,
    LOCK_SETTINGS_LOCKED_LAYOUT: BOOLEAN_REGEX,
    LOCK_SETTINGS_LOCK_ON_JOIN: BOOLEAN_REGEX,
    LOCK_SETTINGS_LOCK_ON_JOIN_CONFIGURABLE: BOOLEAN_REGEX,
    LOGIN_URL: URL_REGEX,
    LOGO: URL_REGEX,
    LOGOUT_URL: URL_REGEX,
    MAX_PARTICIPANTS: NUMBER_REGEX,
    MEETING_CAMERA_CAP: NUMBER_REGEX,
    MEETING_EXPIRE_IF_NO_USER_JOINED_IN_MINUTES: NUMBER_REGEX,
    MEETING_EXPIRE_WHEN_LAST_USER_LEFT_IN_MINUTES: NUMBER_REGEX,
    MEETING_KEEP_EVENT: BOOLEAN_REGEX,
    MEETING_LAYOUT: MEETING_LAYOUT_REGEX,
    META_FULLAUDIO_BRIDGE: AUDIO_BRIDGE_REGEX,
    MODERATOR_ONLY_MESSAGE: ANY_REGEX,
    MUTE_ON_START: BOOLEAN_REGEX,
    NOTIFY_RECORDING_IS_ON: BOOLEAN_REGEX,
    PLUGIN_MANIFESTS: ANY_REGEX,
    PRE_UPLOADED_PRESENTATION: URL_REGEX,
    PRE_UPLOADED_PRESENTATION_NAME: ANY_REGEX,
    PRE_UPLOADED_PRESENTATION_OVERRIDE_DEFAULT: BOOLEAN_REGEX,
    PRESENTATION_UPLOAD_EXTERNAL_DESCRIPTION: ANY_REGEX,
    PRESENTATION_UPLOAD_EXTERNAL_URL: URL_REGEX,
    RECORD: BOOLEAN_REGEX,
    RECORD_FULL_DURATION_MEDIA: BOOLEAN_REGEX,
    WEBCAMS_ONLY_FOR_MODERATOR: BOOLEAN_REGEX,
    WELCOME: ANY_REGEX,

    # Join
    ERROR_REDIRECT_URL: URL_REGEX,
    EXCLUDE_FROM_DASHBOARD: BOOLEAN_REGEX,
    ROLE: ROLE_REGEX,
    USERDATA_BBB_ASK_FOR_FEEDBACK_ON_LOGOUT: BOOLEAN_REGEX,
    USERDATA_BBB_AUTO_JOIN_AUDIO: BOOLEAN_REGEX,
    USERDATA_BBB_AUTO_SHARE_WEBCAM: BOOLEAN_REGEX,
    USERDATA_BBB_AUTO_SWAP_LAYOUT: BOOLEAN_REGEX,
    USERDATA_BBB_CLIENT_TITLE: ANY_REGEX,
    USERDATA_BBB_CUSTOM_STYLE: ANY_REGEX,
    USERDATA_BBB_CUSTOM_STYLE_URL: URL_REGEX,
    USERDATA_BBB_DEFAULT_LAYOUT: MEETING_LAYOUT_REGEX,
    USERDATA_BBB_DISPLAY_BRANDING_AREA: BOOLEAN_REGEX,
    USERDATA_BBB_ENABLE_SCREEN_SHARING: BOOLEAN_REGEX,
    USERDATA_BBB_ENABLE_VIDEO: BOOLEAN_REGEX,
    USERDATA_BBB_FORCE_LISTEN_ONLY: BOOLEAN_REGEX,
    USERDATA_BBB_FORCE_RESTORE_PRESENTATION_ON_NEW_EVENTS: BOOLEAN_REGEX,
    USERDATA_BBB_FULL_AUDIO_BRIDGE: BOOLEAN_REGEX,
    USERDATA_BBB_HIDE_CONTROLS: BOOLEAN_REGEX,
    USERDATA_BBB_HIDE_NOTIFICATIONS: BOOLEAN_REGEX,
    USERDATA_BBB_HIDE_PRESENTATION: BOOLEAN_REGEX,
    USERDATA_BBB_HIDE_PRESENTATION_ON_JOIN: BOOLEAN_REGEX,
    USERDATA_BBB_LISTEN_ONLY_MODE: BOOLEAN_REGEX,
    USERDATA_BBB_MIRROR_OWN_WEBCAM: BOOLEAN_REGEX,
    USERDATA_BBB_MULTI_USER_PEN_ONLY: BOOLEAN_REGEX,
    USERDATA_BBB_MULTI_USER_TOOLS: ANY_REGEX,
    USERDATA_BBB_OUTSIDE_TOGGLE_RECORDING: BOOLEAN_REGEX,
    USERDATA_BBB_OUTSIDE_TOGGLE_SELF_VOICE: BOOLEAN_REGEX,
    USERDATA_BBB_OVERRIDE_DEFAULT_LOCALE: LOCALE_REGEX,
    USERDATA_BBB_PREFER_DARK_THEME: BOOLEAN_REGEX,
    USERDATA_BBB_PREFERRED_CAMERA_PROFILE: CAMERA_REGEX,
    USERDATA_BBB_PRESENTER_TOOLS: ANY_REGEX,
    USERDATA_BBB_RECORD_VIDEO: BOOLEAN_REGEX,
    USERDATA_BBB_SHORTCUTS: ANY_REGEX,
    USERDATA_BBB_SHOW_PARTICIPANTS_ON_LOGIN: BOOLEAN_REGEX,
    USERDATA_BBB_SHOW_PUBLIC_CHAT_ON_LOGIN: BOOLEAN_REGEX,
    USERDATA_BBB_SKIP_CHECK_AUDIO: BOOLEAN_REGEX,
    USERDATA_BBB_SKIP_CHECK_AUDIO_ON_FIRST_JOIN: BOOLEAN_REGEX,
    USERDATA_BBB_SKIP_ECHOTEST_IF_PREVIOUS_DEVICE: BOOLEAN_REGEX,
    USERDATA_BBB_SKIP_VIDEO_PREVIEW: BOOLEAN_REGEX,
    USERDATA_BBB_SKIP_VIDEO_PREVIEW_ON_FIRST_JOIN: BOOLEAN_REGEX,
    WEBCAM_BACKGROUND_URL: URL_REGEX
}