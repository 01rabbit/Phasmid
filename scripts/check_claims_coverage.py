#!/usr/bin/env python3
"""Check coverage mapping between docs/CLAIMS.md and tests.

SH-17 requirements:
- parse claim IDs from CLAIMS.md
- detect CLM references in tests
- report unverified claim count
- emit JSON report for release artifacts
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

CLAIM_ID_RE = re.compile(r"CLM-\d+")
TEST_CLAIM_RE = re.compile(r"CLM[-_]?(\d+)")


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    claim_text: str
    source: str
    verification: str
    scope: str


def _canon_claim_id(raw: str) -> str:
    match = TEST_CLAIM_RE.search(raw)
    if not match:
        return raw.strip()
    return f"CLM-{int(match.group(1))}"


def parse_claims_table(path: Path) -> list[ClaimRecord]:
    if not path.exists():
        raise FileNotFoundError(f"claims file not found: {path}")
    claims: list[ClaimRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cols = [item.strip() for item in line.strip().strip("|").split("|")]
        if len(cols) < 5:
            continue
        claim_id, claim_text, source, verification, scope = cols[:5]
        if not CLAIM_ID_RE.fullmatch(claim_id):
            continue
        claims.append(
            ClaimRecord(
                claim_id=_canon_claim_id(claim_id),
                claim_text=claim_text,
                source=source,
                verification=verification,
                scope=scope,
            )
        )
    if not claims:
        raise ValueError(f"no claim rows found in {path}")
    return claims


def collect_test_claim_ids(tests_dir: Path) -> set[str]:
    found: set[str] = set()
    for path in tests_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in TEST_CLAIM_RE.finditer(text):
            found.add(f"CLM-{int(match.group(1))}")
    return found


def build_report(claims: list[ClaimRecord], test_claim_ids: set[str]) -> dict:
    unverified: list[str] = []
    test_claims: list[str] = []
    manual_claims: list[str] = []
    uncovered_test_claims: list[str] = []

    for claim in claims:
        verification = claim.verification.lower()
        if "unverified" in verification:
            unverified.append(claim.claim_id)
        if verification.startswith("tests:") or verification.startswith("test:"):
            test_claims.append(claim.claim_id)
            if claim.claim_id not in test_claim_ids:
                uncovered_test_claims.append(claim.claim_id)
        elif verification == "manual":
            manual_claims.append(claim.claim_id)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claims_total": len(claims),
        "claims_test_verified": len(test_claims),
        "claims_manual_verified": len(manual_claims),
        "claims_unverified": len(unverified),
        "claims_unverified_ids": sorted(unverified),
        "claims_test_references_found": len(test_claim_ids),
        "claims_marked_test_but_not_found": sorted(uncovered_test_claims),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check CLAIMS.md coverage mapping")
    parser.add_argument(
        "--claims-file", default="docs/CLAIMS.md", help="Path to claims markdown file"
    )
    parser.add_argument("--tests-dir", default="tests", help="Path to tests directory")
    parser.add_argument(
        "--output",
        default="release/local/claims_coverage.json",
        help="Path to JSON report",
    )
    parser.add_argument(
        "--max-unverified",
        type=int,
        default=8,
        help="Fail when unverified claim count exceeds this value",
    )
    args = parser.parse_args(argv)

    claims = parse_claims_table(Path(args.claims_file))
    test_claim_ids = collect_test_claim_ids(Path(args.tests_dir))
    report = build_report(claims, test_claim_ids)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        "claims coverage: "
        f"total={report['claims_total']} "
        f"test={report['claims_test_verified']} "
        f"manual={report['claims_manual_verified']} "
        f"unverified={report['claims_unverified']}"
    )

    if report["claims_unverified"] > args.max_unverified:
        print(
            "error: unverified claims exceed threshold "
            f"({report['claims_unverified']} > {args.max_unverified})"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
