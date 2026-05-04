# Solution Readiness Plan

This plan defines what must be true before Phasmid should be presented as more than a field-evaluation prototype.

The goal is not to add broad new features. The goal is to make the current local-only appliance behavior repeatable, testable, and honestly bounded.

## Product Boundary

Phasmid may be treated as an operational solution only for deployment conditions that have been tested and recorded.

The solution boundary is:

- local-only storage;
- localhost or USB gadget access;
- no cloud dependency;
- no telemetry;
- no remote management;
- no communications security claims;
- no anonymity claims;
- no guaranteed deletion claims;
- no approved classified-data handling claims.

## Readiness Gates

Phasmid remains a field-evaluation prototype until all of these readiness gates are completed for a release:

1. automated tests pass;
2. Raspberry Pi Zero 2 W field test is completed;
3. seizure review checklist is completed;
4. systemd service behavior is reviewed;
5. browser cache and response headers are reviewed;
6. shell history and application logs are reviewed;
7. sudden power-loss behavior is reviewed;
8. metadata workflow behavior is reviewed;
9. validation results are recorded in `docs/REVIEW_VALIDATION_RECORD.md`;
10. README claims match the validation record.

## Release Discipline

Each release candidate should record:

- git commit;
- test command;
- test result;
- coverage result;
- formatting and static-analysis result;
- target hardware;
- operating system image;
- service unit used;
- Field Mode setting;
- audit setting;
- network posture;
- release manifest and SBOM generation result;
- known failures;
- remaining unvalidated areas.

## What Would Change the Status

Phasmid can move from field-evaluation prototype to local appliance solution only after target-hardware validation is recorded.

Even then, the claim should remain narrow:

```text
Validated local-only coercion-aware storage appliance for the recorded deployment conditions.
```

It should not become:

```text
Certified secure storage.
Guaranteed deletion.
Approved classified-data infrastructure.
General-purpose secure communications.
Remote management platform.
```

## Current Status

Current status is defined by `docs/REVIEW_VALIDATION_RECORD.md`.

At the time this plan was added, automated tests had passed on a development machine, and target-hardware validation had not yet been recorded.
