# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2021 IBH IT-Service GmbH
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
# for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


RETURN_STRING_GET_MEETINGS_NO_MEETINGS = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<meetings/>\r\n<messageKey>noMeetings</messageKey>\r\n<message>no meetings were found on this server</message>\r\n</response>'
RETURN_STRING_CHECKSUM_MATCH_ERROR = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>checksumError</messageKey>\r\n<message>Checksums do not match</message>\r\n</response>'
RETURN_STRING_VERSION = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<version>2.0</version>\r\n</response>'
RETURN_STRING_CREATE_FAILED = '<response>\r\n<returncode>FAILED</returncode>\r\n<message>No node available.</message>\r\n</response>'
RETURN_STRING_CREATE_LIMIT_REACHED = '<response>\r\n<returncode>FAILED</returncode>\r\n<message>Meeting/Attendee limit reached.</message>\r\n</response>'
RETURN_STRING_IS_MEETING_RUNNING_FALSE = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<running>false</running>\r\n</response>'
RETURN_STRING_GET_MEETING_NOT_FOUND = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>notFound</messageKey>\r\n<message>We could not find a meeting with that meeting ID - perhaps the meeting is not yet running?</message>\r\n</response>'
RETURN_STRING_GET_RECORDING_TEXT_TRACKS_NOTHING_FOUND_JSON = '{"response":{"returncode":"FAILED","messageKey":"noRecordings","message":"No recording found"}}'
RETURN_STRING_GET_RECORDING_NO_RECORDINGS = '<response>\r\n<returncode>SUCCESS</returncode>\r\n<recordings></recordings>\r\n<messageKey>noRecordings</messageKey>\r\n<message>There are no recordings for the meeting(s).</message>\r\n</response>'
RETURN_STRING_MISSING_MEETING_ID = '<response>\r\n<returncode>FAILED</returncode>\r\n<messageKey>missingParamMeetingID</messageKey>\r\n<message>You must specify a meeting ID for the meeting.</message>\r\n</response>'
RETURN_STRING_GENERAL_FAILED = "<response>\n\t<returncode>SUCCESS</returncode>\n\t<{}>false</{}>\n</response>"
MAX_BASE64_SLIDE_SIZE_IN_POST = 1024000
# 1024000 * 0.75 ~ 768kB -> max file size in post
MAX_SLIDE_SIZE_IN_POST = MAX_BASE64_SLIDE_SIZE_IN_POST * 0.75
