from __future__ import annotations

import os
from typing import Any, cast

import cv2
import numpy as np


class FaceSampleMatcher:
    """Face sample extraction and template comparison without session concerns."""

    def __init__(
        self,
        *,
        face_size: tuple[int, int],
        mse_threshold: float,
        correlation_threshold: float,
        hist_threshold: float,
    ) -> None:
        self.face_size = face_size
        self.mse_threshold = mse_threshold
        self.correlation_threshold = correlation_threshold
        self.hist_threshold = hist_threshold
        cascade_path = os.path.join(
            cast(Any, cv2).data.haarcascades, "haarcascade_frontalface_default.xml"
        )
        self.detector = cv2.CascadeClassifier(cascade_path)

    def collect_samples(self, frames):
        samples = []
        for frame in frames:
            if frame is None:
                continue
            sample = self.face_sample(frame)
            if sample is not None:
                samples.append(sample)
        return samples

    def face_sample(self, frame):
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = self.detector.detectMultiScale(
            gray, scaleFactor=1.08, minNeighbors=4, minSize=(64, 64)
        )
        if len(faces) < 1:
            return None
        faces = sorted(faces, key=lambda item: item[2] * item[3], reverse=True)
        x, y, w, h = cast(Any, faces[0])
        pad_x = int(w * 0.15)
        pad_y = int(h * 0.20)
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(gray.shape[1], x + w + pad_x)
        y1 = min(gray.shape[0], y + h + pad_y)
        face = gray[y0:y1, x0:x1]
        if face.size == 0:
            return None
        resized = cv2.resize(face, self.face_size, interpolation=cv2.INTER_AREA)
        normalized = cv2.equalizeHist(resized).astype(np.float32)
        return normalized

    def correlation(self, left, right):
        left_flat = left.reshape(-1)
        right_flat = right.reshape(-1)
        left_norm = left_flat - np.mean(left_flat)
        right_norm = right_flat - np.mean(right_flat)
        denom = float(np.linalg.norm(left_norm) * np.linalg.norm(right_norm))
        if denom == 0.0:
            return 0.0
        return float(np.dot(left_norm, right_norm) / denom)

    def histogram_similarity(self, left, right):
        left_hist = cv2.calcHist([left.astype(np.uint8)], [0], None, [32], [0, 256])
        right_hist = cv2.calcHist([right.astype(np.uint8)], [0], None, [32], [0, 256])
        cv2.normalize(left_hist, left_hist)
        cv2.normalize(right_hist, right_hist)
        return float(cv2.compareHist(left_hist, right_hist, cv2.HISTCMP_CORREL))

    def matches_any_template(self, sample, templates):
        for template in templates:
            mse = float(np.mean((sample - template) ** 2))
            corr = self.correlation(sample, template)
            hist = self.histogram_similarity(sample, template)
            if mse <= self.mse_threshold and (
                corr >= self.correlation_threshold or hist >= self.hist_threshold
            ):
                return True
        return False
