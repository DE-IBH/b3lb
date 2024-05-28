from django.conf import settings
from hashlib import sha1, sha256, sha384, sha512
from _hashlib import HASH
from re import compile, escape
from typing import Any, Dict

#
# CONSTANTS
#
API_MATE_CHAR_POOL = 'abcdefghijklmnopqrstuvwxyz0123456789'
CONTENT_TYPE = "text/xml"
HOST_REGEX = compile(r'([^:]+)(:\d+)?$')
MEETING_ID_LENGTH = 100
MEETING_NAME_LENGTH = 256
NONCE_CHAR_POOL = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@*(-_)'
NONCE_LENGTH = 64
RECORD_PROFILE_DESCRIPTION_LENGTH = 255
RETURN_STRING_VERSION = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<version>2.0</version>\r\n<apiVersion>2.0</apiVersion>\r\n<bbbVersion/>\r\n</response>'
RETURN_STRING_CREATE_LIMIT_REACHED = '<response>\r\n<returncode>FAILED</returncode>\r\n<message>Meeting/Attendee limit reached.</message>\r\n</response>'
RETURN_STRING_CREATE_NO_NODE_AVAILABE = '<response>\r\n<returncode>FAILED</returncode>\r\n<message>No Node available.</message>\r\n</response>'
RETURN_STRING_IS_MEETING_RUNNING_FALSE = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<running>false</running>\r\n</response>'
RETURN_STRING_GET_MEETING_INFO_FALSE = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>notFound</messageKey>\r\n<message>A meeting with that ID does not exist</message>\r\n</response>'
RETURN_STRING_GET_MEETINGS_NO_MEETINGS = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<meetings/>\r\n<messageKey>noMeetings</messageKey>\r\n<message>no meetings were found on this server</message>\r\n</response>'
RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON = '{"response":{"returncode":"FAILED","messageKey":"noRecordings","message":"No recording found"}}'
RETURN_STRING_GET_RECORDING_NO_RECORDINGS = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<recordings></recordings>\r\n<messageKey>noRecordings</messageKey>\r\n<message>There are no recordings for the meeting(s).</message>\r\n</response>'
RETURN_STRING_MISSING_MEETING_ID = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>missingParamMeetingID</messageKey>\r\n<message>You must specify a meeting ID for the meeting.</message>\r\n</response>'
RETURN_STRING_MISSING_MEETING_ID_TO_LONG = '<response>\r\n<returncode>FAILED</returncode>\r\n<message>Meeting id must be between 2 and 100 characters</message>\r\n</response>'
RETURN_STRING_MISSING_RECORD_ID = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>missingParamRecordID</messageKey>\r\n<message>You must specify one or more a record IDs.</message>\r\n</response>'
RETURN_STRING_MISSING_RECORD_PUBLISH = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>missingParamPublish</messageKey>\r\n<message>You must specify one a publish value true or false.</message>\r\n</response>'
RETURN_STRING_RECORD_PUBLISHED = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<published>{}</published>\r\n</response>'
RETURN_STRING_RECORD_DELETED = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<deleted>true</deleted>\r\n</response>'
RETURN_STRING_RECORD_UPDATED = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<updated>true</updated>\r\n</response>'
RETURN_STRING_WRONG_MEETING_NAME_LENGTH = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>sizeError</messageKey>\r\n<message>Meeting name must be between 2 and 256 characters</message>\r\n</response>'
SHA1 = "sha1"
SHA256 = "sha256"
SHA384 = "sha384"
SHA512 = "sha512"
SHA_BY_STRING: Dict[str, HASH] = {SHA1: sha1, SHA256: sha256, SHA384: sha384, SHA512: sha512}
SHA_ALGORITHMS: Dict[Any, HASH] = {}
for desc, length, algorithm in [(SHA1, 40, sha1), (SHA256, 64, sha256), (SHA384, 96, sha384), (SHA512, 128, sha512)]:
    if desc in settings.B3LB_ALLOWED_SHA_ALGORITHMS:
        SHA_ALGORITHMS[length] = algorithm
        SHA_ALGORITHMS[desc] = algorithm
SLUG_REGEX = compile(r'^([a-z]{2,10})(-(\d{3}))?\.' + escape(settings.B3LB_API_BASE_DOMAIN) + '$')
