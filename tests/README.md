# Test Suite Guide

This directory contains unit, scenario, property, and policy tests.

## Layout

- `tests/test_*.py`: core unit and integration tests
- `tests/scenarios/`: scenario-driven checks and fixtures
- `tests/crypto/`: cryptographic policy/invariant checks
- `tests/properties/`: property-based invariant tests
- `tests/webui/`: WebUI/source-leakage focused checks

## Maintenance rules

- Keep tests aligned with current docs paths. When docs move to `docs/archive/`, update tests that read those files.
- Prefer updating assertions to current public contracts rather than pinning historical README wording.
- Do not check in cache artifacts such as `__pycache__/`.

## Retention policy

See `tests/TEST_RETENTION_MATRIX.md` for keep/consolidate/optional/archive-review classification.

## Default command

```bash
python3 -m unittest discover -s tests
```

## Optional profile

```bash
python3 -m unittest discover -s tests_optional
```

## Archive-review profile

```bash
python3 -m unittest discover -s tests_archive_review
```

Note: some tests require optional dependencies (for example `fastapi`, `cryptography`, `numpy`, `cv2`, `hypothesis`).
In minimal environments, dependency-related import errors are expected until requirements are installed.
