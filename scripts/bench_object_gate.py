import argparse
import os
import sys
import time
import tracemalloc

import numpy as np

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.object_gate import ObjectGate
from phasmid.recognition_benchmark import RecognitionBenchmark


def _textured_bgr(h: int, w: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    for i in range(0, h, max(8, h // 12)):
        base[i, :] = 255
    for j in range(0, w, max(8, w // 12)):
        base[:, j] = 255
    return base


def _temperature_c() -> str:
    path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read().strip()
        return f"{int(raw) / 1000.0:.1f}"
    except (OSError, ValueError):
        return "unavailable"


def _resolution(value: str) -> tuple[int, int]:
    width, height = value.lower().split("x", 1)
    return int(width), int(height)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local object gate paths.")
    parser.add_argument(
        "--method",
        choices=("orb", "akaze", "model", "combined"),
        default="orb",
    )
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--resolution", default="320x240")
    args = parser.parse_args()

    width, height = _resolution(args.resolution)
    reference = _textured_bgr(height, width, seed=1)
    probes = [_textured_bgr(height, width, seed=idx + 2) for idx in range(args.frames)]

    tracemalloc.start()
    started_wall = time.perf_counter()
    started_cpu = time.process_time()

    benchmark = RecognitionBenchmark()
    notes = ""
    stable_frames = 0
    result_state = "rejected"

    if args.method in ("orb", "akaze"):
        summary = benchmark.run_object_benchmark(
            reference_frame=reference,
            probe_frames=probes,
            algo=args.method,
        )
        elapsed_ms = int((time.perf_counter() - started_wall) * 1000)
        stable_frames = summary.accept_count
        result_state = "accepted" if summary.accept_count else "rejected"
        avg_frame_ms = summary.latency_ms_mean
        notes = summary.notes or "feature matcher benchmark"
    else:
        gate = ObjectGate()
        results = []
        for frame in probes:
            orb_match = {"inliers": 24} if args.method == "combined" else None
            results.append(gate.evaluate_frame(frame=frame, orb_match=orb_match))
        elapsed_ms = int((time.perf_counter() - started_wall) * 1000)
        stable_frames = sum(1 for item in results if item.state == "accepted")
        result_state = results[-1].state if results else "no_signal"
        avg_frame_ms = elapsed_ms / max(len(results), 1)
        notes = "model backend unavailable by default" if args.method == "model" else "combined gate path"

    cpu_elapsed = time.process_time() - started_cpu
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    cpu_percent = 0.0
    wall_seconds = max(time.perf_counter() - started_wall, 0.001)
    cpu_percent = (cpu_elapsed / wall_seconds) * 100.0

    print(f"method={args.method}")
    print(f"resolution={width}x{height}")
    print(f"frames_attempted={args.frames}")
    print(f"stable_frames={stable_frames}")
    print(f"elapsed_ms={elapsed_ms}")
    print(f"avg_frame_ms={avg_frame_ms:.2f}")
    print(f"max_memory_mb={peak / (1024 * 1024):.2f}")
    print(f"cpu_percent={cpu_percent:.1f}")
    print(f"temperature_c={_temperature_c()}")
    print(f"result_state={result_state}")
    print(f"notes={notes}")


if __name__ == "__main__":
    main()
