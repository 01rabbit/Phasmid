# Versioning Policy

Phasmid uses a SemVer-style policy for documented interfaces and operational expectations.

## SemVer Baseline

- `MAJOR`: incompatible changes to documented behavior or compatibility contracts.
- `MINOR`: backward-compatible functionality additions.
- `PATCH`: backward-compatible fixes and maintenance updates.

## Breaking-Change Rules Specific to Phasmid

- Any `vault.bin` format change is a **MAJOR** bump.
- Any removal of an existing claim from `docs/CLAIMS.md` is treated as a **MAJOR** change.

## Prototype Naming Rule

Pre-release prototype tags use:

- `0.x.y-prototype`

Example:

- `0.1.0-prototype`

## Documentation Alignment Requirement

A version update should ship with:

- `CHANGELOG.md` entry,
- updated security-impact notes under `### Security` when applicable,
- claims and non-claims consistency checks (`docs/CLAIMS.md` / `docs/NON_CLAIMS.md`).
