import io
import os
import time

import numpy as np

from .config import (
    FACE_ENROLL_FLAG_NAME,
    FACE_TEMPLATE_NAME,
    STATE_KEY_NAME,
    state_dir,
    ui_face_enroll_seconds,
)
from .face_sample_matcher import FaceSampleMatcher
from .face_session_store import FaceSessionStore
from .local_state_crypto import LocalStateCipher


class FaceUILock:
    FACE_SIZE = (96, 96)
    MAX_TEMPLATES = 7
    VERIFY_REQUIRED = 1
    VERIFY_MAX_FAILURES = 5
    SESSION_TTL_SECONDS = 300
    MSE_THRESHOLD = 7200.0
    CORRELATION_THRESHOLD = 0.32
    HIST_THRESHOLD = 0.62
    ENROLLMENT_TTL_SECONDS = 600

    def __init__(self, state_path=None):
        self.state_dir = state_path or state_dir()
        os.makedirs(self.state_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.state_dir, 0o700)
        except OSError:
            pass
        self.template_path = os.path.join(self.state_dir, FACE_TEMPLATE_NAME)
        self.enrollment_path = os.path.join(self.state_dir, FACE_ENROLL_FLAG_NAME)
        self.state_key_path = os.path.join(self.state_dir, STATE_KEY_NAME)
        self.state_cipher = LocalStateCipher(
            state_key_path=self.state_key_path,
            aad=self._aad(),
            local_key_suffix=b":face-ui-lock",
        )
        self.matcher = FaceSampleMatcher(
            face_size=self.FACE_SIZE,
            mse_threshold=self.MSE_THRESHOLD,
            correlation_threshold=self.CORRELATION_THRESHOLD,
            hist_threshold=self.HIST_THRESHOLD,
        )
        self.session_store = FaceSessionStore(
            ttl_seconds=self.SESSION_TTL_SECONDS,
            verify_max_failures=self.VERIFY_MAX_FAILURES,
        )

    @property
    def sessions(self):
        return self.session_store.sessions

    @property
    def failures(self):
        return self.session_store.failures

    def is_enrolled(self):
        return os.path.exists(self.template_path)

    def enroll_from_frame(self, frame):
        return self.enroll_from_frames([frame])

    def enroll_from_frames(self, frames):
        samples = self._collect_samples(frames)
        if not samples:
            return False, "No usable face detected."
        templates = np.array(samples[: self.MAX_TEMPLATES], dtype=np.float32)
        self._write_templates(templates)
        self.session_store.clear_failures()
        return True, "Face UI lock enrolled."

    def verify_from_frame(self, frame, client_id):
        return self.verify_from_frames([frame], client_id)

    def verify_from_frames(self, frames, client_id):
        if self.session_store.failure_count(client_id) >= self.VERIFY_MAX_FAILURES:
            return False, "Face lock is temporarily unavailable."
        try:
            templates = self._read_templates()
        except (OSError, ValueError):
            return False, "Face UI lock is not enrolled."

        samples = self._collect_samples(frames)
        if not samples:
            self._record_failure(client_id)
            return False, "No usable face detected."

        good = 0
        for sample in samples:
            if self._matches_any_template(sample, templates):
                good += 1

        if good >= min(self.VERIFY_REQUIRED, len(samples)):
            self.session_store.clear_failures(client_id)
            return True, "Face verified."

        self._record_failure(client_id)
        return False, "Face verification failed."

    def create_session(self, client_id, token):
        self.session_store.create_session(client_id, token)

    def session_valid(self, client_id, token):
        return self.session_store.session_valid(client_id, token)

    def clear_session(self, token):
        self.session_store.clear_session(token)

    def reset(self):
        self.session_store.reset()
        if not os.path.exists(self.template_path):
            return True, "Face UI lock is already clear."
        try:
            size = max(os.path.getsize(self.template_path), 1024)
            with open(self.template_path, "r+b") as handle:
                handle.write(os.urandom(size))
                handle.flush()
                os.fsync(handle.fileno())
            os.remove(self.template_path)
        except OSError:
            return False, "Failed to clear face UI lock."
        return True, "Face UI lock cleared."

    def arm_enrollment(self):
        try:
            os.makedirs(self.state_dir, mode=0o700, exist_ok=True)
            with open(self.enrollment_path, "w", encoding="utf-8") as handle:
                handle.write(str(int(time.time())))
            os.chmod(self.enrollment_path, 0o600)
        except OSError:
            return False, "Failed to arm face enrollment."
        return True, "Face enrollment armed for the next UI lock session."

    def enrollment_pending(self, now=None):
        if not os.path.exists(self.enrollment_path):
            return False
        now = time.time() if now is None else now
        try:
            created_at = os.path.getmtime(self.enrollment_path)
        except OSError:
            return False
        if now - created_at > ui_face_enroll_seconds(self.ENROLLMENT_TTL_SECONDS):
            self.clear_enrollment_request()
            return False
        return True

    def clear_enrollment_request(self):
        try:
            os.remove(self.enrollment_path)
        except FileNotFoundError:
            pass
        except OSError:
            return False, "Failed to clear face enrollment request."
        return True, "Face enrollment request cleared."

    def status(self, client_id=None, token=None):
        return {
            "enabled": True,
            "enrolled": self.is_enrolled(),
            "unlocked": (
                self.session_valid(client_id, token) if client_id is not None else False
            ),
            "max_failures": self.VERIFY_MAX_FAILURES,
            "failures": (
                self.session_store.failure_count(client_id)
                if client_id is not None
                else 0
            ),
        }

    def _record_failure(self, client_id):
        self.session_store.record_failure(client_id)

    def _collect_samples(self, frames):
        return self.matcher.collect_samples(frames)

    def _face_sample(self, frame):
        return self.matcher.face_sample(frame)

    def _write_templates(self, templates):
        payload = io.BytesIO()
        np.savez_compressed(payload, templates=templates)
        encrypted = self._encrypt(payload.getvalue())
        with open(self.template_path, "wb") as handle:
            handle.write(encrypted)
        try:
            os.chmod(self.template_path, 0o600)
        except OSError:
            pass

    def _read_templates(self):
        with open(self.template_path, "rb") as handle:
            data = handle.read()
        plaintext = self.state_cipher.decrypt(
            data,
            too_short_message="face template is too short",
            auth_failed_message="face template authentication failed",
        )
        with np.load(io.BytesIO(plaintext), allow_pickle=False) as payload:
            if "templates" in payload:
                templates = payload["templates"].astype(np.float32)
                if templates.ndim == 2:
                    return templates.reshape((1, *templates.shape))
                return templates
            return payload["template"].astype(np.float32).reshape((1, *self.FACE_SIZE))

    def _encrypt(self, plaintext):
        return self.state_cipher.encrypt(plaintext)

    def _state_encryption_key(self):
        return self.state_cipher.encryption_key()

    def _load_or_create_local_state_key(self):
        return self.state_cipher._load_or_create_local_state_key()

    def _aad(self):
        return b"phasmid-ui-face-lock:v1"

    def _correlation(self, left, right):
        return self.matcher.correlation(left, right)

    def _matches_any_template(self, sample, templates):
        return self.matcher.matches_any_template(sample, templates)

    def _histogram_similarity(self, left, right):
        return self.matcher.histogram_similarity(left, right)


face_lock = FaceUILock()
