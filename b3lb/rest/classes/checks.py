from django.conf import settings
from hashlib import sha1, sha256
from rest.models import Node
from typing import Any, Dict, List


class NodeCheck:
    PARAMETERS_INT: List[str]
    PARAMETERS_STR: List[str]
    node: Node
    has_errors: bool
    attendees: int
    meetings: int
    meeting_stats: Dict[str, Dict[str, Any]]

    def add_meeting_to_stats(self, meeting_id: str):
        self.meeting_stats[meeting_id] = {}
        for param in self.PARAMETERS_INT:
            self.meeting_stats[meeting_id][param] = 0
        for param in self.PARAMETERS_STR:
            self.meeting_stats[meeting_id][param] = ""

    def get_meetings_url(self) -> str:
        if settings.B3LB_SHA_ALGORITHM == "sha1":
            sha = sha1()
        elif settings.B3LB_SHA_ALGORITHM == "sha256":
            sha = sha256()
        else:
            sha = sha1()

        sha.update(f"getMeetings{self.node.secret}".encode())
        return f"{self.node.api_base_url}getMeetings?checksum={sha.hexdigest()}"

    def __init__(self, uuid: str):
        self.node = Node.objects.get(uuid=uuid)
        self.has_errors = True
        self.attendees = 0
        self.meetings = 0
        self.meeting_stats = {}
        self.PARAMETERS_INT = ["participantCount", "listenerCount", "voiceParticipantCount", "videoCount", "moderatorCount"]
        self.PARAMETERS_STR = ["bbb-origin", "bbb-origin-server-name"]
