from __future__ import annotations

from typing import Any, cast

import cv2
import numpy as np


class ObjectCueMatcher:
    """ORB-based object-cue matching isolated from camera and UI concerns."""

    def __init__(
        self,
        *,
        min_reference_keypoints: int,
        min_frame_descriptors: int,
        min_good_matches: int,
        min_inliers: int,
    ) -> None:
        self.min_reference_keypoints = min_reference_keypoints
        self.min_frame_descriptors = min_frame_descriptors
        self.min_good_matches = min_good_matches
        self.min_inliers = min_inliers
        self.orb = cast(Any, cv2).ORB_create(nfeatures=1000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING)

    def empty_reference(self) -> dict[str, object | None]:
        return {
            "kp": None,
            "des": None,
            "shape": None,
            "pts": None,
            "path": None,
        }

    def to_gray(self, image):
        return cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))

    def _reference_corners(self, h: int, w: int):
        points: Any = [[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]
        return cast(Any, np.float32(points)).reshape(-1, 1, 2)

    def reference_state_from_image(self, image):
        if image is None:
            return None

        gray = self.to_gray(image)
        kp, des = self.orb.detectAndCompute(gray, None)
        if not kp or len(kp) < self.min_reference_keypoints or des is None:
            return None

        h, w = gray.shape
        return {
            "kp": kp,
            "des": des,
            "shape": (h, w),
            "pts": self._reference_corners(h, w),
            "path": None,
        }

    def reference_state_from_arrays(self, des, kp_data, shape):
        kp = [
            cv2.KeyPoint(
                x=float(row[0]),
                y=float(row[1]),
                size=float(row[2]),
                angle=float(row[3]),
                response=float(row[4]),
                octave=int(row[5]),
                class_id=int(row[6]),
            )
            for row in kp_data
        ]
        if not kp or des is None or len(kp) < self.min_reference_keypoints:
            return self.empty_reference()

        shape = tuple(int(v) for v in shape)
        h, w = shape
        return {
            "kp": kp,
            "des": des,
            "shape": shape,
            "pts": self._reference_corners(h, w),
            "path": None,
        }

    def match_reference_state(self, ref_state, frame_gray):
        ref_des = ref_state["des"]
        ref_kp = ref_state["kp"]
        ref_pts = ref_state["pts"]
        if ref_des is None or ref_kp is None or ref_pts is None or frame_gray is None:
            return None

        kp, des = self.orb.detectAndCompute(frame_gray, None)
        if des is None or len(des) <= self.min_frame_descriptors:
            return None

        return self.match_descriptors(ref_state, kp, des)

    def match_descriptors(self, ref_state, kp, des):
        ref_des = ref_state["des"]
        ref_kp = ref_state["kp"]
        if ref_des is None or ref_kp is None or des is None or kp is None:
            return None

        matches = self.bf.knnMatch(ref_des, des, k=2)
        good_matches = []
        for pair in matches:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        if len(good_matches) <= self.min_good_matches:
            return None

        src_points: Any = [ref_kp[m.queryIdx].pt for m in good_matches]
        src_pts = cast(Any, np.float32(src_points)).reshape(
            -1, 1, 2
        )
        dst_points: Any = [kp[m.trainIdx].pt for m in good_matches]
        dst_pts = cast(Any, np.float32(dst_points)).reshape(
            -1, 1, 2
        )
        homography, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if homography is None or mask is None:
            return None

        inliers = int(mask.ravel().tolist().count(1))
        if inliers <= self.min_inliers:
            return None

        return {
            "homography": homography,
            "inliers": inliers,
        }
