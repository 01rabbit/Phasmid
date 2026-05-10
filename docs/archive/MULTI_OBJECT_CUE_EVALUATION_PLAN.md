# Multi-Object Cue and Visual Sequence Evaluation Plan (Issue #20)

## Purpose

This document defines an analysis plan for evaluating multi-object cues and short visual sequence matching as operational access-cue enhancements.

The goal is to improve reliability and operator control while preserving neutral capture-visible behavior and the existing cryptographic boundary.

## Constraints

- Camera cues remain operational gates, not cryptographic secrets.
- No direct cryptographic dependence on unstable coordinates, bounding boxes, or frame-order artifacts.
- No cloud services or remote inference.
- No requirement for heavyweight machine-learning models.
- Neutral UI and API behavior must be preserved.

## Candidate Patterns

### Multi-Object Scene Cue

- Two or more registered objects in one frame.
- Relation checks:
  - left/right ordering
  - above/below ordering
  - minimum relative distance bucket

### Visual Sequence Cue

- Short sequence of cue states over time.
- Example sequence token model:
  - `object_a_visible`
  - `object_b_visible`
  - `relation_ok`
- Sequence validation uses bounded windows and timeout limits.

### Stability and Ambiguity

- Require stable acceptance across a frame window.
- Reject ambiguous scenes that satisfy multiple candidate cues.
- Preserve explicit `ambiguous` state and neutral reject behavior.

## Measurement Plan

Target hardware baseline:

- Raspberry Pi Zero 2 W
- Camera Module 3 NoIR Wide (or equivalent)

For each pattern, record:

- false accept observations
- false reject observations
- latency (p50/p95)
- CPU and memory behavior
- thermal behavior
- operator retry burden

Test dimensions:

- lighting variation
- angle variation
- distance variation
- placement jitter
- motion blur
- partial occlusion

## Threat and Failure Analysis Checklist

- photo/screen replay observations
- scene ambiguity when multiple cues are present
- stress-path behavior under repeated rejection
- capture-visible branch leakage risk
- failure behavior when no object is visible

## Recommendation Outcomes

- reject
- documentation-only
- minimal implementation (experimental/off by default)

Any implementation recommendation must define:

- neutral API contract
- neutral UI wording
- bounded runtime policy
- explicit non-cryptographic boundary statement

## Proposed Neutral API Shape (Analysis Draft)

```json
{
  "camera_ready": true,
  "object_state": "none|detected|matched|ambiguous",
  "cue_confidence": 0.0,
  "sequence_state": "idle|collecting|matched|timeout|ambiguous"
}
```

## Out of Scope

- biometric identity claims
- anti-spoof guarantees
- compliance/certification claims
- automatic route disclosure in user-visible surfaces
