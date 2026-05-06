import argparse
import os
import statistics
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.vault_core import PhasmidVault


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Phasmid vault Argon2id parameters."
    )
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument(
        "--memory-cost", type=int, default=PhasmidVault.ARGON2_MEMORY_COST
    )
    parser.add_argument(
        "--iterations", type=int, default=PhasmidVault.ARGON2_ITERATIONS
    )
    parser.add_argument("--lanes", type=int, default=PhasmidVault.ARGON2_LANES)
    args = parser.parse_args()

    timings = []
    with tempfile.TemporaryDirectory() as tmp:
        vault = PhasmidVault(
            os.path.join(tmp, "vault.bin"),
            size_mb=1,
            state_dir=os.path.join(tmp, "state"),
        )
        vault.ARGON2_MEMORY_COST = args.memory_cost
        vault.ARGON2_ITERATIONS = args.iterations
        vault.ARGON2_LANES = args.lanes
        vault.format_container()

        sequence = ["reference_dummy_matched"]
        for _ in range(args.rounds):
            started = time.perf_counter()
            vault.store(
                "benchmark-password",
                b"x" * 1024,
                sequence,
                filename="bench.bin",
                mode="dummy",
            )
            result, _ = vault.retrieve("benchmark-password", sequence, mode="dummy")
            elapsed = time.perf_counter() - started
            if result != b"x" * 1024:
                raise RuntimeError("benchmark round failed")
            timings.append(elapsed)

    print(f"rounds={args.rounds}")
    print(
        f"memory_cost={args.memory_cost} iterations={args.iterations} lanes={args.lanes}"
    )
    print(
        f"min={min(timings):.3f}s median={statistics.median(timings):.3f}s max={max(timings):.3f}s"
    )


if __name__ == "__main__":
    main()
