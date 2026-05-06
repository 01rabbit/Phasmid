from __future__ import annotations

from typing import Any

import cv2


class CameraFrameSource:
    """Thin wrapper around OpenCV capture lifecycle for local camera frames."""

    def __init__(self, *, frame_size: tuple[int, int]) -> None:
        self.frame_size = frame_size
        self.cap: Any | None = None

    def open(self) -> None:
        if self.cap is not None:
            return
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_size[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_size[1])

    def read(self):
        self.open()
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self) -> None:
        if self.cap is None:
            return
        self.cap.release()
        self.cap = None
