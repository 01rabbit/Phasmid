"""
Lightweight face recognizer using Haar Cascade detection + LBP histogram matching.

Requires only base opencv-python-headless (no opencv-contrib).
Designed for on-demand, single-attempt use on constrained hardware such as
Raspberry Pi Zero 2 W.  It must never be used as a source of cryptographic
key material.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceRecognitionResult:
    """Neutral recognition result.  Not cryptographic material."""

    face_detected: bool
    confidence: float  # 0.0–1.0; higher = more similar to enrolled face
    status: str  # "not_enrolled" | "no_face" | "low_confidence" | "accepted"


class LightweightFaceRecognizer:
    """
    Face detection via Haar Cascade + recognition via LBP histogram matching.

    Enrollment stores normalised LBP histograms.  Prediction computes
    chi-square distance between the probe histogram and each enrolled
    template, returning the minimum distance converted to a confidence
    score.

    This is an experimental evaluation component.  It is not a substitute
    for a hardware-backed biometric system and must remain behind an
    optional operator gate.
    """

    FACE_SIZE: tuple[int, int] = (64, 64)
    MAX_ENROLL_TEMPLATES: int = 7
    # Chi-square distance below which a probe is accepted (lower = stricter).
    ACCEPT_CHI_DISTANCE: float = 0.50
    # Haar Cascade detection parameters
    SCALE_FACTOR: float = 1.08
    MIN_NEIGHBORS: int = 4
    MIN_FACE_PX: int = 48

    def __init__(self) -> None:
        cascade_path: str = cast(Any, cv2).data.haarcascades + "haarcascade_frontalface_default.xml"
        self._detector = cv2.CascadeClassifier(cascade_path)
        self._templates: list[np.ndarray] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enroll(self, frames: list[np.ndarray]) -> bool:
        """
        Enroll from a list of BGR frames.  Returns True if at least one
        face sample was extracted and stored.
        """
        samples: list[np.ndarray] = []
        for frame in frames:
            hist = self._extract_lbp_histogram(frame)
            if hist is not None:
                samples.append(hist)
            if len(samples) >= self.MAX_ENROLL_TEMPLATES:
                break
        if not samples:
            return False
        self._templates = samples
        return True

    def predict(self, frame: np.ndarray) -> FaceRecognitionResult:
        """
        Predict whether the face in *frame* matches the enrolled face.
        Returns a :class:`FaceRecognitionResult` with a neutral status.
        """
        if not self._templates:
            return FaceRecognitionResult(
                face_detected=False,
                confidence=0.0,
                status="not_enrolled",
            )
        probe = self._extract_lbp_histogram(frame)
        if probe is None:
            return FaceRecognitionResult(
                face_detected=False,
                confidence=0.0,
                status="no_face",
            )
        min_dist = min(
            self._chi_square_distance(probe, tmpl) for tmpl in self._templates
        )
        confidence = self._distance_to_confidence(min_dist)
        if min_dist < self.ACCEPT_CHI_DISTANCE:
            return FaceRecognitionResult(
                face_detected=True,
                confidence=confidence,
                status="accepted",
            )
        return FaceRecognitionResult(
            face_detected=True,
            confidence=confidence,
            status="low_confidence",
        )

    def clear(self) -> None:
        self._templates = []

    @property
    def is_enrolled(self) -> bool:
        return bool(self._templates)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_lbp_histogram(self, frame: np.ndarray) -> np.ndarray | None:
        """Detect largest face, resize, compute normalised LBP histogram."""
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        faces = self._detector.detectMultiScale(
            gray,
            scaleFactor=self.SCALE_FACTOR,
            minNeighbors=self.MIN_NEIGHBORS,
            minSize=(self.MIN_FACE_PX, self.MIN_FACE_PX),
        )
        if not len(faces):
            return None
        faces_list = cast(Any, faces)
        faces_sorted = sorted(faces_list, key=lambda r: r[2] * r[3], reverse=True)
        x, y, w, h = faces_sorted[0]
        face_crop = gray[y : y + h, x : x + w]
        if face_crop.size == 0:
            return None
        face_resized = cv2.resize(face_crop, self.FACE_SIZE, interpolation=cv2.INTER_AREA)
        return self._lbp_histogram(face_resized)

    def _lbp_histogram(self, face_gray: np.ndarray) -> np.ndarray:
        """
        Compute an 8-neighbour LBP map and return a normalised 256-bin histogram.

        Each pixel encodes the pattern of its 8 neighbours (clockwise from
        top-left) as a single byte.  The histogram captures the texture
        distribution of the face region without storing raw pixel data.
        """
        center = face_gray[1:-1, 1:-1].astype(np.int16)
        neighbors: list[np.ndarray] = [
            face_gray[0:-2, 0:-2],  # top-left
            face_gray[0:-2, 1:-1],  # top
            face_gray[0:-2, 2:],    # top-right
            face_gray[1:-1, 2:],    # right
            face_gray[2:, 2:],      # bottom-right
            face_gray[2:, 1:-1],    # bottom
            face_gray[2:, 0:-2],    # bottom-left
            face_gray[1:-1, 0:-2],  # left
        ]
        lbp = np.zeros(center.shape, dtype=np.uint8)
        for bit, neighbor in enumerate(neighbors):
            bits: np.ndarray = (neighbor.astype(np.int16) >= center).astype(np.uint8)
            lbp = lbp | (bits << bit).astype(np.uint8)

        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        hist = hist.astype(np.float32)
        total = float(hist.sum())
        if total > 0.0:
            hist /= total
        return hist

    def _chi_square_distance(self, h1: np.ndarray, h2: np.ndarray) -> float:
        """Symmetric chi-square distance between two normalised histograms."""
        denom = h1 + h2 + 1e-10
        return float(np.sum((h1 - h2) ** 2 / denom))

    def _distance_to_confidence(self, distance: float) -> float:
        """
        Convert a chi-square distance to a confidence score in [0.0, 1.0].
        A distance of zero maps to 1.0; distances at or beyond
        ACCEPT_CHI_DISTANCE map to approximately 0.0.
        """
        return float(max(0.0, 1.0 - distance / max(self.ACCEPT_CHI_DISTANCE, 1e-10)))
