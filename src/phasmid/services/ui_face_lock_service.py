from __future__ import annotations

from ..face_lock import face_lock


class UIFaceLockService:
    """Boundary service for UI face-lock state, enrollment, and verification."""

    def __init__(self):
        self.face_lock = face_lock

    def session_valid(self, client_id, token):
        return self.face_lock.session_valid(client_id, token)

    def status(self, client_id=None, token=None):
        return self.face_lock.status(client_id, token)

    def is_enrolled(self):
        return self.face_lock.is_enrolled()

    def enrollment_pending(self):
        return self.face_lock.enrollment_pending()

    def enroll_from_frames(self, frames):
        return self.face_lock.enroll_from_frames(frames)

    def clear_enrollment_request(self):
        return self.face_lock.clear_enrollment_request()

    def verify_from_frames(self, frames, client_id):
        return self.face_lock.verify_from_frames(frames, client_id)

    def create_session(self, client_id, token):
        self.face_lock.create_session(client_id, token)

    def clear_session(self, token):
        self.face_lock.clear_session(token)

    @property
    def session_ttl_seconds(self):
        return self.face_lock.SESSION_TTL_SECONDS


ui_face_lock_service = UIFaceLockService()
