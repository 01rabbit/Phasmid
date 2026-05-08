#!/usr/bin/env python3
"""
scripts/pi_zero2w/run_local_perf.py

Performance and timing measurement script for Raspberry Pi Zero 2 W.
Executed ON the Pi by run_remote_perf.sh via SSH.

Design constraints (do not change without updating the Issue spec):
  - All vault operations use PhasmidVault with mode="dummy" (headless).
    "phasmid store" and "phasmid retrieve" require a physical camera and
    CANNOT be called from this script.
  - CLI commands that need .state/ are run with CWD = repo root and with
    PHASMID_STATE_DIR set to an absolute path under _pi_field_test/.
  - "phasmid doctor" is always called with --no-tui.
  - PHASMID_TMPFS_STATE must NOT be set in the environment when this
    script runs (run_remote_perf.sh strips it before SSHing).
  - Partial failures are recorded and do not abort remaining phases.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

# Allow import from src/ when run directly from the repo root on the Pi.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

_VENV_PHASMID = str(_REPO_ROOT / ".venv" / "bin" / "phasmid")
_TEST_DIR = _REPO_ROOT / "_pi_field_test"


# ── Utility helpers ────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _temp_c() -> float | None:
    for path in ("/sys/class/thermal/thermal_zone0/temp",):
        try:
            return int(Path(path).read_text().strip()) / 1000.0
        except (OSError, ValueError):
            pass
    return None


def _mem_available_kb() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return None


def _swap_enabled() -> bool:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("SwapTotal:"):
                return int(line.split()[1]) > 0
    except (OSError, ValueError):
        pass
    return False


def _git_commit() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT),
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ── Phase D: Import-time baseline ─────────────────────────────────────────────

def measure_imports() -> dict:
    modules = [
        "cryptography",
        "argon2",
        "numpy",
        "cv2",
        "fastapi",
        "uvicorn",
        "textual",
        "phasmid.vault_core",
        "phasmid.observability_probe",
        "phasmid.kdf_engine",
    ]
    results = []
    for name in modules:
        t0 = time.perf_counter()
        try:
            __import__(name)
            elapsed = time.perf_counter() - t0
            results.append({"module": name, "status": "ok", "elapsed_s": round(elapsed, 4)})
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            results.append({"module": name, "status": "failed",
                             "elapsed_s": round(elapsed, 4), "error": str(exc)})
    return {"imports": results}


# ── Phase E: CLI baseline ──────────────────────────────────────────────────────

def measure_cli_baseline(state_dir: str) -> dict:
    env = {
        **os.environ,
        "PHASMID_AUDIT": "0",
        "PHASMID_DEBUG": "0",
        "PHASMID_STATE_DIR": state_dir,
    }
    # PHASMID_TMPFS_STATE must not be set. Remove it defensively.
    env.pop("PHASMID_TMPFS_STATE", None)

    commands = {
        "help":         [_VENV_PHASMID, "--help"],
        "doctor":       [_VENV_PHASMID, "doctor", "--no-tui"],
        "verify_state": [_VENV_PHASMID, "verify-state"],
    }
    results = {}
    for name, cmd in commands.items():
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=90,
                cwd=str(_REPO_ROOT),
                env=env,
            )
            elapsed = time.perf_counter() - t0
            results[name] = {
                "status": "ok" if proc.returncode == 0 else "nonzero",
                "returncode": proc.returncode,
                "elapsed_s": round(elapsed, 4),
                "stdout_lines": len(proc.stdout.decode(errors="replace").splitlines()),
            }
        except subprocess.TimeoutExpired:
            results[name] = {"status": "timeout", "elapsed_s": 90.0}
        except Exception as exc:
            results[name] = {"status": "error", "error": str(exc)}
    return {"cli_baseline": results}


# ── Phase F: Vault operations (headless, mode="dummy") ────────────────────────
# phasmid store / phasmid retrieve require a camera and CANNOT be used here.
# PhasmidVault with mode="dummy" is the only supported headless path.

def measure_vault_operations() -> dict:
    from phasmid.vault_core import PhasmidVault

    with tempfile.TemporaryDirectory(prefix="phasmid_vault_bench_") as tmp:
        vault = PhasmidVault(
            os.path.join(tmp, "vault.bin"),
            size_mb=1,
            state_dir=os.path.join(tmp, ".state"),
        )
        payload = b"phasmid-field-test-payload-" * 40  # ~1 kB
        sequence = ["reference_dummy_matched"]

        t0 = time.perf_counter()
        vault.format_container()
        format_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        vault.store("bench-passphrase", payload, sequence,
                    filename="bench.bin", mode="dummy")
        store_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        result, _ = vault.retrieve("bench-passphrase", sequence, mode="dummy")
        retrieve_s = time.perf_counter() - t0

        return {
            "vault_operations": {
                "format_s":     round(format_s, 4),
                "store_s":      round(store_s, 4),
                "retrieve_s":   round(retrieve_s, 4),
                "roundtrip_ok": result == payload,
                "payload_bytes": len(payload),
            }
        }


# ── Phase G: KDF timing ───────────────────────────────────────────────────────

def measure_kdf(rounds: int = 3) -> dict:
    from phasmid.vault_core import PhasmidVault

    with tempfile.TemporaryDirectory(prefix="phasmid_kdf_bench_") as tmp:
        vault = PhasmidVault(
            os.path.join(tmp, "vault.bin"),
            size_mb=1,
            state_dir=os.path.join(tmp, ".state"),
        )
        vault.format_container()
        sequence = ["reference_dummy_matched"]
        timings = []

        for _ in range(rounds):
            t0 = time.perf_counter()
            vault.store("bench-passphrase", b"x" * 256, sequence,
                        filename="bench.bin", mode="dummy")
            vault.retrieve("bench-passphrase", sequence, mode="dummy")
            timings.append(time.perf_counter() - t0)

        return {
            "kdf_timing": {
                "rounds":       rounds,
                "min_s":        round(min(timings), 4),
                "median_s":     round(statistics.median(timings), 4),
                "max_s":        round(max(timings), 4),
                "memory_cost_kib": vault.ARGON2_MEMORY_COST,
                "iterations":   vault.ARGON2_ITERATIONS,
                "lanes":        vault.ARGON2_LANES,
            }
        }


# ── Phase H: Object-gate / ORB (synthetic frames) ─────────────────────────────

def measure_object_gate() -> dict:
    try:
        import numpy as np

        from phasmid.recognition_benchmark import RecognitionBenchmark

        rng = np.random.default_rng(42)
        h, w = 240, 320
        reference = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
        probes    = [rng.integers(0, 256, (h, w, 3), dtype=np.uint8) for _ in range(5)]

        bench = RecognitionBenchmark()
        t0 = time.perf_counter()
        summary = bench.run_object_benchmark(
            reference_frame=reference,
            probe_frames=probes,
            algo="orb",
        )
        elapsed_s = time.perf_counter() - t0

        return {
            "object_gate": {
                "status":        "ok",
                "method":        "orb",
                "resolution":    f"{w}x{h}",
                "frames":        len(probes),
                "elapsed_s":     round(elapsed_s, 4),
                "avg_frame_ms":  round(summary.latency_ms_mean, 2),
                "p50_ms":        round(summary.latency_ms_p50, 2),
                "p95_ms":        round(summary.latency_ms_p95, 2),
                "accept_count":  summary.accept_count,
                "note": ("Synthetic frames — compute cost only, "
                         "no real recognition accuracy implied"),
            }
        }
    except Exception as exc:
        return {"object_gate": {"status": "failed", "error": str(exc)}}


# ── Phase N: Coercion-path timing consistency ──────────────────────────────────
# This is a required test. It measures Phasmid's central security property:
# that NORMAL, FAILED, and RESTRICTED code paths are not distinguishable by
# timing observation on real Pi hardware.
#
# Acceptance gate: max_timing_delta_ms < 5% of kdf_wall_time_ms.
# If the gate fails, overall_status becomes "fail" regardless of other phases.

def measure_coercion_path_timing(n: int = 5) -> dict:
    try:
        import argon2

        from phasmid.observability_probe import ObservabilityProbe

        def _real_kdf(password: bytes, salt: bytes) -> bytes:
            return argon2.low_level.hash_secret_raw(
                password, salt,
                time_cost=3,
                memory_cost=65536,
                parallelism=1,
                hash_len=32,
                type=argon2.low_level.Type.ID,
            )

        probe = ObservabilityProbe(kdf_fn=_real_kdf)
        t0 = time.perf_counter()
        report = probe.measure_all(n=n)
        total_wall_s = time.perf_counter() - t0

        max_delta_ms    = report.max_timing_delta_ms()
        kdf_wall_ms     = (total_wall_s * 1000) / (n * 3)  # 3 paths measured
        threshold_ms    = kdf_wall_ms * 0.05
        gate_passed     = max_delta_ms < threshold_ms

        return {
            "coercion_path_timing": {
                "status":                  "ok",
                "max_timing_delta_ms":     round(max_delta_ms, 4),
                "kdf_wall_time_ms":        round(kdf_wall_ms, 2),
                "gate_threshold_ms":       round(threshold_ms, 4),
                "gate_passed":             gate_passed,
                "n_rounds":                n,
                "paths_with_fs_writes":    report.paths_with_filesystem_writes(),
                "summary":                 report.summary(),
            }
        }
    except Exception as exc:
        return {
            "coercion_path_timing": {
                "status":      "failed",
                "error":       str(exc),
                "gate_passed": False,
            }
        }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pi Zero 2W local performance measurements (runs on the Pi)"
    )
    parser.add_argument(
        "--results-dir",
        default=str(_TEST_DIR / "results"),
        help="Directory to write perf-results.json",
    )
    parser.add_argument("--kdf-rounds",   type=int, default=3)
    parser.add_argument("--probe-rounds", type=int, default=5)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    state_dir = str(_TEST_DIR / ".state")
    Path(state_dir).mkdir(parents=True, exist_ok=True)

    output: dict = {
        "timestamp":               _utc_now(),
        "git_commit":              _git_commit(),
        "swap_enabled":            _swap_enabled(),
        "temperature_before_c":    _temp_c(),
        "mem_available_before_kb": _mem_available_kb(),
        "test_phase_results":      {},
        "failures":                [],
        "warnings":                [],
        "overall_status":          "unknown",
    }

    if output["swap_enabled"]:
        output["warnings"].append(
            "Swap is enabled. Argon2id memory may page to SD card, "
            "affecting KDF timing measurements and data-remanence properties."
        )

    phases = [
        ("imports",              measure_imports),
        ("cli_baseline",         lambda: measure_cli_baseline(state_dir)),
        ("vault_operations",     measure_vault_operations),
        ("kdf_timing",           lambda: measure_kdf(args.kdf_rounds)),
        ("object_gate",          measure_object_gate),
        ("coercion_path_timing", lambda: measure_coercion_path_timing(args.probe_rounds)),
    ]

    for phase_name, fn in phases:
        print(f"[run_local_perf] phase={phase_name} ...", flush=True)
        temp_before = _temp_c()
        try:
            result = fn()
            output["test_phase_results"][phase_name] = "ok"
            output.update(result)
            temp_after = _temp_c()
            if temp_before is not None:
                output.setdefault("temperature", {})[f"{phase_name}_before_c"] = temp_before
            if temp_after is not None:
                output.setdefault("temperature", {})[f"{phase_name}_after_c"] = temp_after
            print(f"[run_local_perf] phase={phase_name} ok", flush=True)
        except Exception as exc:
            output["test_phase_results"][phase_name] = "fail"
            output["failures"].append({"phase": phase_name, "error": str(exc)})
            print(f"[run_local_perf] phase={phase_name} FAILED: {exc}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)

    output["temperature_after_c"]    = _temp_c()
    output["mem_available_after_kb"] = _mem_available_kb()

    # Coercion-path gate failure forces overall_status to fail.
    cpt = output.get("coercion_path_timing", {})
    if cpt.get("gate_passed") is False:
        delta = cpt.get("max_timing_delta_ms", "?")
        threshold = cpt.get("gate_threshold_ms", "?")
        output["failures"].append({
            "phase": "coercion_path_timing",
            "error": (
                f"TIMING GATE FAILED: delta={delta}ms exceeds threshold={threshold}ms. "
                "FAILED/RESTRICTED paths may be timing-distinguishable on this hardware."
            ),
        })

    any_fail = any(v == "fail" for v in output["test_phase_results"].values())
    output["overall_status"] = "fail" if any_fail else "pass"

    out_path = results_dir / "perf-results.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"[run_local_perf] results written to {out_path}", flush=True)

    if output["overall_status"] == "fail":
        sys.exit(1)


if __name__ == "__main__":
    main()
