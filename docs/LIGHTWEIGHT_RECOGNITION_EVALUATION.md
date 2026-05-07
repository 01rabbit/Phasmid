# Lightweight Recognition Evaluation (Issue #38)

## Purpose

Evaluate whether Phasmid should integrate separate lightweight local models for
face recognition and object recognition after the AI gate decoupling work (#27).

The evaluation goal is not a real-time inference pipeline.  It is an on-demand,
single-attempt check that can run within the CPU, memory, and thermal budget of a
Raspberry Pi Zero 2 W.

## Boundary Statement

Recognition outputs are operational gate signals only.  They must never directly
generate, modify, or replace cryptographic key material, KDF inputs, AEAD
parameters, or container layout values.  The access path decision remains in the
policy layer (`ObjectCuePolicyGate`).

---

## Candidate Designs

### Face Gate

The existing `FaceUILock` uses Haar Cascade detection with pixel-level template
comparison (MSE, Pearson correlation, histogram similarity).  This evaluation
examines whether adding an LBP histogram matching step provides a measurable
reliability gain within the Pi Zero 2 W budget.

**Candidate**: `LightweightFaceRecognizer` (`src/phasmid/lightweight_face_recognizer.py`)

- Detection: Haar Cascade (`haarcascade_frontalface_default.xml`), identical to
  the existing face lock.  No additional model file required.
- Recognition: 8-neighbour Local Binary Pattern (LBP) histogram, computed with
  base NumPy and OpenCV.  No `opencv-contrib` dependency.
- Matching: normalised chi-square distance between a 256-bin LBP histogram of the
  probe face and each enrolled template histogram.  Default accept threshold:
  chi-square distance < 0.50.
- Storage: enrolled templates are histogram arrays (`float32`, 256 values each);
  up to 7 templates stored per enrollment session.  No raw pixel data is stored.
- Output: `FaceRecognitionResult(face_detected, confidence, status)` where
  `status` ∈ `{"not_enrolled", "no_face", "low_confidence", "accepted"}`.

**Why LBP over raw pixel matching**:
- Insensitive to uniform illumination shifts; histogram captures texture, not
  absolute brightness.
- Produces a single scalar confidence without requiring expensive nearest-
  neighbour search over raw pixel arrays.
- Implementable entirely in base OpenCV + NumPy; no additional model download.
- Known to run on embedded ARM Cortex-A53 within a single-frame budget at 64×64
  resolution.

**Limitation**: LBP histogram matching does not separate identity well under large
pose variation or heavy occlusion.  It is suitable as an optional UI gate, not as
a biometric authenticator.

### Object Gate

The existing `ObjectCueMatcher` uses ORB (Oriented FAST and Rotated BRIEF) with a
Brute-Force NORM\_HAMMING matcher and RANSAC homography.  This evaluation examines
AKAZE as an alternative backend.

**Candidate**: `LightweightObjectMatcher` (`src/phasmid/lightweight_object_matcher.py`)

Both backends (ORB and AKAZE) are available in `opencv-python-headless` without
additional model files.

| Property | ORB | AKAZE |
|---|---|---|
| Descriptor type | Binary (BRIEF) | Binary (MLDB, default) |
| BFMatcher norm | NORM\_HAMMING | NORM\_HAMMING |
| Typical keypoints per 320×240 frame | 400–800 | 150–400 |
| Scale-space computation | Integer pyramid | Float-domain (slower) |
| Rotation invariance | Moderate | Good |
| Affine robustness | Moderate | Better |
| Pi Zero 2 W per-frame cost (estimated) | < 80 ms | 100–180 ms |

**Recommendation (pre-hardware-validation)**:

ORB is the preferred backend.  It is faster, already deployed in
`ObjectCueMatcher`, and produces sufficient inliers for homography verification
at 320×240.  AKAZE should be re-evaluated only if ORB shows a false-reject rate
> 20% under field lighting conditions.

---

## Benchmark Harness

`RecognitionBenchmark` (`src/phasmid/recognition_benchmark.py`) is an offline
harness that accepts pre-captured BGR frames as NumPy arrays.

```
from phasmid.recognition_benchmark import RecognitionBenchmark

bench = RecognitionBenchmark()

# Face gate benchmark
summary = bench.run_face_benchmark(
    enroll_frames=[...],   # list of BGR np.ndarray
    probe_frames=[...],    # positive probe frames (all should be accepted)
)

# Object gate comparison (ORB vs AKAZE)
report = bench.compare_object_algos(
    reference_frame=...,
    probe_frames=[...],
)
print(report.recommendation())
```

Outputs: `FaceBenchmarkSummary`, `ObjectBenchmarkSummary`, `ComparisonReport`.
All fields are numeric scalars and neutral status strings suitable for recording
in the field test validation document.

---

## Pi Zero 2 W Measurement Plan

Before changing default posture, the following measurements must be recorded on
target hardware.

### Frame Size

Primary: 320×240.  Test 640×480 only if 320×240 shows > 30% false-reject rate.

### Face Gate Procedure

1. Enroll 5–7 frames under standard indoor lighting.
2. Run 20 positive probe frames per condition:
   - standard lighting
   - reduced lighting (50% lux)
   - lateral offset (±20°)
3. Run 10 negative probe frames (different person or blank frame).
4. Record: `accept_rate`, `false_reject_rate`, `latency_ms_p50`, `latency_ms_p95`.
5. Repeat at 64×64 and 96×96 face crop size.

### Object Gate Procedure

1. Enroll reference object under neutral lighting.
2. Run 20 positive probe frames per condition:
   - same lighting as enrollment
   - rotated ±30°
   - partial occlusion (25%)
3. Record for both ORB and AKAZE: `accept_rate`, `inliers_p50`,
   `latency_ms_p50`, `latency_ms_p95`.
4. Compare via `compare_object_algos` → record `ComparisonReport.recommendation()`.

### Acceptance Gate

Before enabling either recogniser in a default operator flow:

- Face gate: `accept_rate` > 0.80 on positive probes, `false_reject_rate` < 0.20
  under standard lighting, `latency_ms_p95` < 500 ms.
- Object gate: `accept_rate` > 0.85 on positive probes,
  `latency_ms_p95` < 200 ms.
- No measurement should claim indistinguishability between operational paths.
- No result should be used to directly key a cryptographic operation.

If any acceptance gate fails, the feature must remain off by default.

---

## Current Status

**Prototype complete — hardware validation pending.**

| Component | Status |
|---|---|
| `LightweightFaceRecognizer` | Implemented, unit-tested, mypy clean |
| `LightweightObjectMatcher` (ORB + AKAZE) | Implemented, unit-tested, mypy clean |
| `RecognitionBenchmark` harness | Implemented, unit-tested |
| Pi Zero 2 W face gate measurements | Not yet recorded |
| Pi Zero 2 W object gate measurements | Not yet recorded |
| Production integration | Not yet; feature remains experimental and off by default |

---

## Next Validation Gate

1. Run the measurement plan on Pi Zero 2 W and record results in the review
   validation record.
2. If acceptance gates pass, add optional operator configuration to route
   face-lock verification through `LightweightFaceRecognizer`.
3. If AKAZE acceptance gate passes and ORB does not, revisit the object gate
   backend choice.
4. Do not promote either recogniser to default-on until both acceptance gates
   are met and the cryptographic boundary review is confirmed.
