# Contributing to Phasmid

This repository accepts focused, reviewable contributions that preserve Phasmid's local-only and honest-interface boundary.

## Scope and Security Discipline

- Do not submit scope-creep features (for example: telemetry, cloud recovery, remote unlock/wipe, or default non-local networking).
- Keep changes aligned with `AGENTS.md`, `docs/THREAT_MODEL.md`, and `docs/SPECIFICATION.md`.
- Prefer one issue per pull request. Keep security-sensitive behavior changes isolated from unrelated refactors.

## Claim Change Policy

- If a change adds, removes, or materially modifies a user-visible security or behavior claim, do all of the following in the same pull request.
- Update [`docs/CLAIMS.md`](docs/CLAIMS.md).
- Add or update tests that verify the claim (or explicitly mark and justify why verification is manual-only).
- Keep `README.md` and related docs aligned with the resulting claim boundary.

## Cryptography Change Policy

- Any cryptography-impacting change requires prior issue discussion before implementation.
- This includes changes to key derivation, container format, key-material lifecycle, encryption/decryption logic, or compatibility/migration behavior.
- Pull requests without a linked and discussed issue may be closed without merge.

## DCO and CLA

- DCO is required for all contributions.
- Sign commits with `Signed-off-by: Your Name <you@example.com>` (for example, `git commit -s`).
- Phasmid does not currently require a separate CLA.

## Minimum Validation Before PR

- Run: `python3 -m unittest discover -s tests`
- For Python changes, also run: `python3 -m ruff check .` and `python3 -m mypy src`
- For self-hardening issues that require it, run additional checks listed in the issue (for example `black --check` and `bandit`).
