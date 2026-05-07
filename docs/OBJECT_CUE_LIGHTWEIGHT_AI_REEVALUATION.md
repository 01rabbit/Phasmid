# Object Cue Lightweight AI Re-Evaluation (Pi Zero 2 W)

## Goal

Re-evaluate whether a lightweight offline AI model can improve object-cue
matching reliability on Raspberry Pi Zero 2 W without breaking local-only and
capture-quiet constraints.

## Current Baseline

- Current access cue matcher is classical feature matching (ORB, with AKAZE as
  benchmark candidate).
- This is fast and offline, but can be brittle under severe blur, low light,
  and viewpoint drift.

## Candidate AI Direction

- Add an optional second-stage verifier using a compact quantized embedding
  model (INT8), executed fully offline.
- Keep ORB as stage 1 for fast reject.
- Run AI verifier only on borderline ORB outcomes to constrain latency.

## Proposed Two-Stage Pipeline

1. Stage 1 (fast gate): ORB matcher returns `accept / reject / borderline`.
2. Stage 2 (only for borderline): model embedding similarity check.
3. Final decision:
   - accept if both stages support accept,
   - reject if both stages reject,
   - otherwise return neutral failure (`no valid entry found`).

## Pi Zero 2 W Feasibility Notes

- Feasible only with strict constraints:
  - low input resolution (for example `96x96` to `128x128`),
  - INT8 model,
  - inference runtime budget under ~120 ms per borderline frame,
  - bounded memory footprint.
- If these targets are not met, keep ORB-only mode as default.

## Model Provisioning Flow

- Normal Phasmid operation must not auto-download models.
- Model fetch is an explicit operator or evaluator step.
- Default fetch command:

```bash
python3 scripts/fetch_object_model.py
```

- Default enable sequence after fetch:

```bash
export PHASMID_OBJECT_MODEL_PATH="$PWD/models/object_gate/mobilenet_v2_1.0_224_feature_vector.tflite"
export PHASMID_EXPERIMENTAL_OBJECT_MODEL=1
```

- If the model file is absent, the experimental path must remain neutral and
  report model unavailability rather than changing vault behavior.

## Measurement Plan

- Compare ORB-only vs ORB+AI on the same frame sets:
  - accept rate,
  - false reject rate,
  - median and p95 latency,
  - CPU utilization and thermal throttling signs.
- Pass gate for optional rollout:
  - false reject improvement >= 15% relative in hard scenes,
  - p95 latency increase <= 150 ms on Pi Zero 2 W.

## Non-Goals

- No cloud inference.
- No biometric identity claims.
- No change to cryptographic key path.
