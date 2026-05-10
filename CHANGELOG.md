# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows SemVer-style release intent for documented interfaces.

## [Unreleased]

No unreleased entries.

## [0.1.3] - 2026-05-10

### Added

- M6 release-discipline controls for reproducible artifact generation, dependency audit checks, and release policy documentation.
- Raspberry Pi environment bootstrap and validation scripts for target-hardware setup and checks.
- Pi Zero 2 W LUKS calibration profile and helper scripts for constrained-device measurement workflows.

### Changed

- Raspberry Pi deployment and validation documentation expanded across setup, field test procedure, seizure review checklist, and readiness planning.
- Release and validation records updated to reflect Pi Zero 2 W evaluation workflow expectations.

### Security

- Dependency vulnerability scanning via `pip-audit` in CI.
- Reproducible-build verification job added to CI to detect artifact drift.

## [0.1.2] - 2026-05-09

### Added

- Raspberry Pi-first camera backend flow with Picamera2/libcamera as primary and OpenCV as fallback.

### Fixed

- WebUI camera stream/status synchronization so `/status` reflects active streaming state.
- MJPEG streaming resilience under camera frame acquisition failures with explicit fallback frame behavior.
- WebUI process termination robustness: graceful stop with forced termination fallback when shutdown hangs.
- Camera resource cleanup lifecycle on WebUI shutdown and stream disconnect paths.
- Raspberry Pi camera color handling and stream orientation for WebUI preview consistency.

### Changed

- TUI/WebUI operator-facing WebUI exposure messaging aligned to non-localhost gadget-access operation.
- WebUI runtime observability expanded for camera backend, readiness, and stream attributes.

### Security

- Existing WebUI protections (token checks, restricted confirmations, rate limits, headers, and restricted-action policy) preserved while introducing Raspberry Pi operational hardening.

## [0.1.1] - 2026-05-09

### Fixed

- TUI-launched WebUI now starts the FastAPI app through `uvicorn` reliably.
- Extended WebUI startup wait to 10 seconds to support Raspberry Pi Zero 2 W class hardware.
- WebUI launch failures now retain actionable diagnostics (attempted command, return code, port-check status, and log path) for operator troubleshooting.

### Changed

- TUI-launched WebUI default bind host changed to `0.0.0.0` for Raspberry Pi USB gadget network access.
- TUI success notification updated to guide access via the device USB gadget IP.

### Security

- Existing WebUI protections (token checks, restricted confirmations, rate limits, and headers) remain unchanged while enabling gadget-network exposure.

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
