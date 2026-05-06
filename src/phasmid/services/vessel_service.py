from __future__ import annotations

import json
from pathlib import Path

from ..models.vessel import VesselMeta, VesselPosture
from .profile_service import _ensure_dir, config_dir

_REGISTRY_PATH_KEY = "vessel_registry"

REVEALING_TERMS = frozenset(
    {
        "secret",
        "hidden",
        "janus",
        "real",
        "fake",
        "decoy",
        "true",
        "covert",
    }
)


def _registry_path() -> Path:
    return config_dir() / "vessel_registry.json"


def _load_registry() -> list[str]:
    rp = _registry_path()
    if not rp.exists():
        return []
    try:
        with open(rp, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [str(p) for p in data.get("vessels", [])]
    except Exception:
        return []


def _save_registry(paths: list[str]) -> None:
    rp = _registry_path()
    _ensure_dir(rp.parent)
    with open(rp, "w", encoding="utf-8") as f:
        json.dump({"vessels": paths}, f, indent=2)
    try:
        rp.chmod(0o600)
    except OSError:
        pass


def register_vessel(path: str | Path) -> None:
    path = str(Path(path).resolve())
    existing = _load_registry()
    if path not in existing:
        existing.append(path)
        _save_registry(existing)


def unregister_vessel(path: str | Path) -> bool:
    path = str(Path(path).resolve())
    existing = _load_registry()
    if path in existing:
        existing.remove(path)
        _save_registry(existing)
        return True
    return False


def list_vessels(extra_dir: str | None = None) -> list[VesselMeta]:
    paths: list[Path] = []

    for p in _load_registry():
        pp = Path(p)
        if pp.exists():
            paths.append(pp)

    if extra_dir:
        ed = Path(extra_dir).expanduser()
        if ed.is_dir():
            for f in ed.glob("*.vessel"):
                if f not in paths:
                    paths.append(f)

    return [_meta_for(p) for p in paths]


def _meta_for(path: Path) -> VesselMeta:
    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    return VesselMeta(
        path=path,
        name=path.name,
        size_bytes=size,
        header_status="absent",
        magic_bytes_status="absent",
        face_count=0,
        posture=VesselPosture.OPERATIONAL if size > 0 else VesselPosture.UNKNOWN,
    )


def check_filename_warnings(path: str | Path) -> list[str]:
    name = Path(path).name.lower()
    warnings = []
    for term in REVEALING_TERMS:
        if term in name:
            warnings.append(
                f'Filename contains revealing term "{term}". '
                "Consider using a neutral name."
            )
    return warnings


def redact_path(path: str | Path) -> str:
    p = Path(path)
    home = Path.home()
    try:
        rel = p.relative_to(home)
        parts = rel.parts
        if len(parts) > 3:
            return f"~/{parts[0]}/.../{parts[-1]}"
        return f"~/{rel}"
    except ValueError:
        return str(p)


class VesselService:
    def register(self, path: str | Path) -> None:
        register_vessel(path)

    def unregister(self, path: str | Path) -> bool:
        return unregister_vessel(path)

    def list_all(self, extra_dir: str | None = None) -> list[VesselMeta]:
        return list_vessels(extra_dir)

    def check_filename_warnings(self, path: str | Path) -> list[str]:
        return check_filename_warnings(path)

    def redact_path(self, path: str | Path) -> str:
        return redact_path(path)
