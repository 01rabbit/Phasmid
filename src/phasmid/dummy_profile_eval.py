from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DummyProfileEvaluation:
    container_size_bytes: int
    dummy_size_bytes: int
    file_count: int
    occupancy_ratio: float
    min_file_size: int
    p50_file_size: int
    max_file_size: int
    warnings: list[str]


def _percentile(sorted_values: list[int], percentile: float) -> int:
    if not sorted_values:
        return 0
    idx = int((len(sorted_values) - 1) * percentile)
    return sorted_values[idx]


def _collect_file_sizes(path: Path) -> list[int]:
    if not path.exists() or not path.is_dir():
        return []
    sizes: list[int] = []
    for item in path.rglob("*"):
        if item.is_file():
            try:
                sizes.append(item.stat().st_size)
            except OSError:
                continue
    return sizes


def evaluate_dummy_profile(
    *,
    dummy_profile_dir: str | Path,
    container_path: str | Path,
    min_size_mb: int,
    min_file_count: int,
    occupancy_warn_threshold: float,
) -> DummyProfileEvaluation:
    dummy_dir = Path(dummy_profile_dir)
    container = Path(container_path)

    file_sizes = sorted(_collect_file_sizes(dummy_dir))
    file_count = len(file_sizes)
    dummy_size_bytes = sum(file_sizes)
    min_size_bytes = max(0, int(min_size_mb) * 1024 * 1024)

    try:
        container_size_bytes = container.stat().st_size
    except OSError:
        container_size_bytes = 0

    occupancy_ratio = 0.0
    if container_size_bytes > 0:
        occupancy_ratio = dummy_size_bytes / float(container_size_bytes)

    warnings: list[str] = []
    if file_count < max(0, min_file_count):
        warnings.append("dummy profile file count is below configured minimum")
    if dummy_size_bytes < min_size_bytes:
        warnings.append("dummy profile size is below configured minimum")
    if container_size_bytes > 0 and occupancy_ratio < max(
        0.0, occupancy_warn_threshold
    ):
        warnings.append(
            "dummy profile size is disproportionately small relative to the local container"
        )

    min_file_size = file_sizes[0] if file_sizes else 0
    p50_file_size = _percentile(file_sizes, 0.5)
    max_file_size = file_sizes[-1] if file_sizes else 0

    return DummyProfileEvaluation(
        container_size_bytes=container_size_bytes,
        dummy_size_bytes=dummy_size_bytes,
        file_count=file_count,
        occupancy_ratio=occupancy_ratio,
        min_file_size=min_file_size,
        p50_file_size=p50_file_size,
        max_file_size=max_file_size,
        warnings=warnings,
    )


def human_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    size = float(value)
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PiB"
