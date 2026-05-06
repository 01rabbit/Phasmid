# Multi-Object Cue Recommendation (Issue #20)

## Decision

Current recommendation: **minimal implementation (experimental only), default off**.

The repository now includes:

- a neutral evaluation plan
- an experimental policy-gate prototype for sequence and ambiguity handling
- ambiguity and no-object regression tests

This is enough to continue analysis work safely without changing cryptographic behavior.

## Why Not Default-On Yet

- No Raspberry Pi Zero 2 W hardware benchmark record has been captured for this issue.
- Lighting/angle/distance stress behavior for multi-object relation checks is not yet field-validated.
- Replay and operator-stress observations are not yet recorded in a target-hardware run log.

## Boundary Statement

Multi-object and visual-sequence outputs remain operational gate signals only.
They are not key material and must not directly affect KDF inputs, AEAD parameters, or container layout values.

## Next Validation Gate

Before changing default posture:

1. run target-hardware benchmarks across lighting, angle, and placement jitter
2. record false reject/false accept observations and operator retry burden
3. verify neutral capture-visible behavior under ambiguous scenes
4. confirm no cryptographic-boundary coupling is introduced

If any gate fails, keep the feature experimental or reject deployment use.
