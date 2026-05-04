# Janus Eidolon System

Janus Eidolon System is the formal architecture name for Phasmid's two-slot disclosure model.

The architecture separates visible disclosure from protected local state under practical risks such as device seizure, compelled access, over-disclosure, metadata leakage, and local UI or log exposure. In this repository, "Janus System" is the short form used for the two-slot model, and "JES" is reserved for technical documents.

## Scope

JES is a local-only storage architecture. It is intended to support:

- local encrypted container storage in `vault.bin`
- password-based recovery
- local access-key mixing
- object-cue guided access flows
- optional UI face lock as a local interface gate
- restricted local update paths with explicit confirmation

JES does not change the project's research-software boundary. It does not imply certified classified-data handling, covert communication, deniability guarantees, remote control, or protection against compromised hosts.

## Core Model

The Janus System uses a two-slot container layout. One slot supports ordinary visible disclosure, and the other protects additional local state behind separate conditions. The implementation keeps normal WebUI and CLI surfaces neutral and avoids exposing internal slot semantics during routine use.

The architecture depends on separation of conditions rather than on misleading UI language. Quiet user-visible surfaces, local state separation, typed restricted confirmation, and controlled local access-path invalidation are all part of that design.

## Implementation Boundary

Within this repository, Phasmid is the user-facing tool and JES is the architecture behind it.

- Use "Phasmid" for product, CLI, WebUI, packaging, deployment, and operator documentation.
- Use "Janus Eidolon System" in architecture and security design discussions.
- Use "Janus System" only as a short architectural label for the two-slot disclosure model.
- Use "JES" only in technical documentation where repetition would otherwise be distracting.

## Security Posture

JES inherits the same operational limits as Phasmid:

- local-only operation by default
- no guarantee of secure deletion
- no protection against live memory capture or malware
- no claim of perfect deniability
- no remote management, unlock, or wipe behavior

Field safety still depends on target-hardware validation, review records, and seizure-review testing.
