# Phasmid Architecture

Phasmid is a field-evaluation prototype for local-only coercion-aware storage and the reference implementation of the Janus Eidolon System.

## Architectural Layers

Phasmid is organized into a few narrow local layers:

1. CLI and WebUI entry points coordinate local operations without exposing internal disclosure structure in normal capture-visible flows.
2. Restricted-action policy checks enforce confirmation, timing, and capability requirements for sensitive local updates.
3. The cryptographic core manages `vault.bin`, key derivation, container layout, record encryption, and local access-key mixing.
4. Local state modules manage typed state, attempt limiting, face-lock state, object-cue material, and optional audit records.
5. Deployment and review documents define the operating boundary for field evaluation and appliance hardening.

## Naming Boundary

Phasmid is the only active product and implementation name in this repository.

- Python package: `src/phasmid`
- Console script: `phasmid`
- WebUI module path: `python3 -m phasmid.web_server`
- Environment variables: `PHASMID_*`

The repository does not keep legacy import paths, wrapper modules, or environment-variable aliases.

## Local Security Boundary

The architecture preserves these constraints:

- `vault.bin` alone is not sufficient for normal recovery when required local state is absent
- object cues are operational access cues, not cryptographic secrets
- Experimental face-lock code is a local interface gate only and is not part of the current WebUI access path
- hidden routes are UX concealment, not access control
- restricted actions require server-side checks and explicit confirmation
- Field Mode reduces exposure but is not a security boundary

## Current Documentation Map

- [docs/SPECIFICATION.md](docs/SPECIFICATION.md) defines implementation behavior and configuration.
- [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) defines assumptions, residual risk, and safety boundaries.
- [docs/JANUS_EIDOLON_SYSTEM.md](docs/JANUS_EIDOLON_SYSTEM.md) defines the formal two-slot architecture.
- [README.md](../README.md) defines the user-facing tool summary and operational limits.
