# Reproducible Builds

Phasmid release-review artifacts are generated with deterministic settings so the same commit can produce bit-for-bit identical outputs.

## Scope

Reproducibility here applies to:

- `MANIFEST.sha256`
- `sbom.cyclonedx.json`
- `release-summary.json`
- `phasmid-release.tar.gz`

via `scripts/generate_release_artifacts.py`.

## Procedure

Use a fixed source date epoch:

```bash
export SOURCE_DATE_EPOCH=1700000000
python3 scripts/generate_release_artifacts.py --output-dir /tmp/repro-a --archive
python3 scripts/generate_release_artifacts.py --output-dir /tmp/repro-b --archive
sha256sum /tmp/repro-a/MANIFEST.sha256 /tmp/repro-a/sbom.cyclonedx.json /tmp/repro-a/release-summary.json /tmp/repro-a/phasmid-release.tar.gz > /tmp/repro-a.sha
sha256sum /tmp/repro-b/MANIFEST.sha256 /tmp/repro-b/sbom.cyclonedx.json /tmp/repro-b/release-summary.json /tmp/repro-b/phasmid-release.tar.gz > /tmp/repro-b.sha
diff -u /tmp/repro-a.sha /tmp/repro-b.sha
```

CI runs this comparison in the `reproducible-build` job.

## Determinism Controls

- Stable file ordering (`sorted` paths).
- Fixed SBOM timestamp from `SOURCE_DATE_EPOCH` (or explicit `--source-date-epoch`).
- Deterministic tar member metadata (uid/gid/uname/gname/mode/mtime).
- Deterministic gzip timestamp (`mtime`).
- Stable JSON key ordering (`sort_keys=True`).

## Known Non-Determinism Sources

- Building from a dirty tree or different commit contents.
- Changing dependency declarations in `pyproject.toml`.
- Different script versions or Python behavior changes outside supported range.
- External files included by mistake outside repository controls.

## Limits

This process provides reproducibility for release-review artifacts, not for all possible runtime environments or OS package layers.
