from __future__ import annotations

import logging
from typing import Any

import cv2

LOG = logging.getLogger(__name__)


class CameraFrameSource:
    """Camera capture wrapper with Picamera2-first backend selection."""

    def __init__(self, *, frame_size: tuple[int, int], fps: int = 5) -> None:
        self.frame_size = frame_size
        self.fps = fps
        self.cap: Any | None = None
        self.picam2: Any | None = None
        self.backend = "none"
        self.last_error: str | None = None

    def open(self) -> None:
        if self.backend != "none":
            return

        if self._open_picamera2():
            return
        if self._open_opencv():
            return

        self.backend = "unavailable"
        if self.last_error is None:
            self.last_error = "camera backend unavailable"
        LOG.error("Camera initialization failed: %s", self.last_error)

    def _open_picamera2(self) -> bool:
        try:
            from picamera2 import Picamera2  # type: ignore[import-not-found]
        except Exception as exc:
            self.last_error = f"Picamera2 import failed: {exc}"
            LOG.warning("%s", self.last_error)
            return False

        try:
            self.picam2 = Picamera2()
            config = self.picam2.create_video_configuration(
                main={"size": self.frame_size, "format": "RGB888"},
                controls={"FrameDurationLimits": (200000, 333333)},
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.backend = "picamera2"
            self.last_error = None
            LOG.info(
                "Camera backend selected: picamera2 (%dx%d @ ~%dfps)",
                self.frame_size[0],
                self.frame_size[1],
                self.fps,
            )
            return True
        except Exception as exc:
            self.last_error = f"Picamera2 startup failed: {exc}"
            LOG.error("%s", self.last_error)
            self._release_picamera2()
            return False

    def _open_opencv(self) -> bool:
        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap is None or not self.cap.isOpened():
                self.last_error = "OpenCV VideoCapture(0) open failed"
                LOG.error("%s", self.last_error)
                self._release_opencv()
                return False
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_size[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_size[1])
            self.cap.set(cv2.CAP_PROP_FPS, float(self.fps))
            self.backend = "opencv"
            self.last_error = None
            LOG.info(
                "Camera backend selected: opencv (%dx%d @ ~%dfps)",
                self.frame_size[0],
                self.frame_size[1],
                self.fps,
            )
            return True
        except Exception as exc:
            self.last_error = f"OpenCV startup failed: {exc}"
            LOG.error("%s", self.last_error)
            self._release_opencv()
            return False

    def read(self):
        self.open()
        if self.backend == "picamera2":
            if self.picam2 is None:
                self.last_error = "Picamera2 backend lost"
                return False, None
            try:
                frame_rgb = self.picam2.capture_array("main")
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                self.last_error = None
                return True, frame_bgr
            except Exception as exc:
                self.last_error = f"Picamera2 frame capture failed: {exc}"
                LOG.error("%s", self.last_error)
                return False, None

        if self.backend == "opencv":
            if self.cap is None:
                self.last_error = "OpenCV backend lost"
                return False, None
            ok, frame = self.cap.read()
            if not ok:
                self.last_error = "OpenCV frame read failed"
                LOG.error("%s", self.last_error)
                return False, None
            self.last_error = None
            return True, frame

        return False, None

    def release(self) -> None:
        self._release_picamera2()
        self._release_opencv()
        self.backend = "none"

    def status(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "ready": self.backend in {"picamera2", "opencv"},
            "last_error": self.last_error,
            "resolution": {"width": self.frame_size[0], "height": self.frame_size[1]},
            "fps_target": self.fps,
        }

    def _release_picamera2(self) -> None:
        if self.picam2 is None:
            return
        try:
            self.picam2.stop()
        except Exception:
            pass
        self.picam2 = None

    def _release_opencv(self) -> None:
        if self.cap is None:
            return
        try:
            self.cap.release()
        except Exception:
            pass
        self.cap = None
