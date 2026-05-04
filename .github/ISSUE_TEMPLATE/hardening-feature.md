---
name: "Security Hardening Feature"
about: "Track a bounded local security hardening improvement for Phasmid"
title: "[FEAT] "
labels: ["hardening", "security"]
assignees: []
---

## Overview

Describe the bounded hardening improvement. Keep wording factual and avoid claims of certification, field-proven assurance, or complete protection.

**Area**:
**Improvement**:
**Priority**: Critical / High / Medium / Low

## Problem Statement

Explain the current limitation and the capture-visible or operational risk it creates.

## Proposed Solution

Describe the implementation approach. If the work is research-only, state that clearly.

## Implementation Scope

- [ ] Cryptographic boundary or key derivation
- [ ] Local key material handling
- [ ] Process or memory hardening
- [ ] WebUI or API surface
- [ ] CLI behavior
- [ ] Audit or diagnostics
- [ ] Tests
- [ ] Documentation

## Compatibility

- **Backward compatibility**:
- **Migration path**:
- **Operational risk**:

## Testing Plan

- [ ] Unit tests
- [ ] Integration tests
- [ ] Target-hardware notes, if applicable
- [ ] Documentation update

## Security Impact

| Threat area | Current limitation | Expected improvement |
| --- | --- | --- |
| Spoofing | | |
| Tampering | | |
| Repudiation | | |
| Information disclosure | | |
| Denial of service | | |
| Elevation of privilege | | |

## Residual Risk

List what remains unsolved after this change. Do not overclaim.

## Acceptance Criteria

- [ ] Implementation matches the documented scope
- [ ] Tests pass
- [ ] User-visible wording remains neutral
- [ ] Threat model or specification updated where needed
- [ ] No cloud, telemetry, remote management, remote wipe, censorship bypass, anonymity routing, covert communication, or offensive capability added
