# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows SemVer-style release intent for documented interfaces.

## [Unreleased]

### Added

- M6 release-discipline controls for reproducible artifact generation, dependency audit checks, and release policy documentation.

### Security

- Dependency vulnerability scanning via `pip-audit` in CI.
- Reproducible-build verification job added to CI to detect artifact drift.

## [0.1.0-prototype] - 2026-05-07

### Added

- Unified JES operator interface (TUI + WebUI alignment and operator pages).
- Threat model consolidation and claim/non-claim documentation baseline.
- Crypto hygiene inventory and tests (nonce, constant-time, randomness checks).
- M3 scenario/property/headerless invariant testing suite.
- M4 operational artifact checks and WebUI source leakage checks.

### Security

- Restricted action policy enforcement and capture-visible response neutrality hardening.
- Process hardening and volatile state support (`PHASMID_TMPFS_STATE`) with diagnostics.
- Optional signed release manifest and SBOM generation.

### Changed

- Terminology alignment toward neutral operator-facing language.

### Documentation

- STRIDE analysis, device-binding analysis, split-key recovery analysis.
- Security policy (`SECURITY.md`) and maintainer continuity note (`docs/BUS_FACTOR.md`).

## Changelog Rule

Security-impacting changes must be listed under a `### Security` section.
