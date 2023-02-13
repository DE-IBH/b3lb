from typing import List

class MeetingStats:
    attendees: int
    meetings: int
    listener_count: int
    voice_participant_count: int
    moderator_count: int
    video_count: int

    def add_meeting_stats(self, attendees: int, listener_count: int, voice_participant_count: int, moderator_count: int, video_count: int):
        self.attendees += attendees
        self.meetings += 1
        self.listener_count += listener_count
        self.voice_participant_count += voice_participant_count
        self.moderator_count += moderator_count
        self.video_count += video_count

    def get_values(self) -> List[int]:
        return [self.meetings, self.attendees, self.listener_count, self.voice_participant_count, self.moderator_count, self.video_count]

    def __init__(self):
        self.attendees = 0
        self.meetings = 0
        self.listener_count = 0
        self.voice_participant_count = 0
        self.moderator_count = 0
        self.video_count = 0
