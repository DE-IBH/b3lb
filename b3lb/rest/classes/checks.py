from rest.b3lb.utils import get_checksum
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
        return f"{self.node.api_base_url}getMeetings?checksum={get_checksum(self.node.cluster.get_sha(), f'getMeetings{self.node.secret}')}"

    def __init__(self, node: Node):
        self.node = node
        self.has_errors = True
        self.attendees = 0
        self.meetings = 0
        self.meeting_stats = {}
        self.PARAMETERS_INT = ["participantCount", "listenerCount", "voiceParticipantCount", "videoCount", "moderatorCount"]
        self.PARAMETERS_STR = ["bbb-origin", "bbb-origin-server-name"]
