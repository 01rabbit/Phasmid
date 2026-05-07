# Dependency Policy

This document defines dependency pinning and update discipline for Phasmid.

## Pinning Rules

- Runtime dependencies are pinned in `requirements.txt` with exact versions (`==`).
- `cryptography` and `argon2-cffi` must remain fully pinned.
- `pyproject.toml` `[project].dependencies` must match runtime dependency intent.
- Development tooling dependencies are pinned in `requirements-dev.txt`.

## Security Checks

- CI runs `pip-audit` for known vulnerability checks.
- CI also runs `bandit` for source-level security scanning.

## Update Cadence

- Default cadence: monthly dependency review.
- Emergency cadence: immediate update for critical security advisories.
- Every update must include:
  - changelog note (`CHANGELOG.md`, include `### Security` when relevant),
  - CI green status,
  - no expansion of project claims beyond documented scope.

## Alignment Expectation

Dependency declarations in:

- `requirements.txt`
- `requirements-dev.txt`
- `pyproject.toml`

must stay consistent with each file’s role (runtime vs development tooling).
