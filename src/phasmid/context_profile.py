"""
Context profile templates for coercion-safe dummy dataset guidance.

A context profile defines the expected content structure for a given operational
context. Profiles guide dummy generation and provide plausibility validation.

Built-in profiles: travel, field_engineer, researcher, maintenance, archive.

Profiles are purely advisory. They do not forge metadata, fake system events,
or perform any anti-forensic tampering.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextProfile:
    profile_name: str
    container_name: str
    expected_size_range: tuple[int, int]  # (min_bytes, max_bytes)
    dummy_content_types: tuple[str, ...]
    description: str
    typical_directories: tuple[str, ...]
    min_file_count: int
    occupancy_ratio_warn: float  # warn when ratio is below this

    def validate(self) -> list[str]:
        """Return a list of plausibility warnings for this profile configuration."""
        warnings: list[str] = []
        min_bytes, max_bytes = self.expected_size_range
        if min_bytes < 0:
            warnings.append("expected_size_range minimum is negative")
        if max_bytes < min_bytes:
            warnings.append("expected_size_range maximum is less than minimum")
        if max_bytes < 1024 * 1024:
            warnings.append("expected_size_range maximum is below 1 MiB — unusually small")
        if self.min_file_count < 1:
            warnings.append("min_file_count is zero — container will appear empty")
        if self.occupancy_ratio_warn < 0.05:
            warnings.append(
                "occupancy_ratio_warn is below 5% — extremely low occupancy may appear suspicious"
            )
        if not self.dummy_content_types:
            warnings.append("no dummy_content_types defined — container will have no file guidance")
        return warnings


BUILT_IN_PROFILES: dict[str, ContextProfile] = {
    "travel": ContextProfile(
        profile_name="travel",
        container_name="travel.vessel",
        expected_size_range=(50 * 1024 * 1024, 2 * 1024 * 1024 * 1024),
        dummy_content_types=("jpg", "jpeg", "png", "txt", "pdf", "html"),
        description=(
            "Travel data carrier. Expected content: photos, itinerary, notes, receipts. "
            "Consistent with a traveler carrying trip documentation."
        ),
        typical_directories=("photos", "itinerary", "notes", "receipts", "maps"),
        min_file_count=20,
        occupancy_ratio_warn=0.10,
    ),
    "field_engineer": ContextProfile(
        profile_name="field_engineer",
        container_name="field.vessel",
        expected_size_range=(20 * 1024 * 1024, 512 * 1024 * 1024),
        dummy_content_types=("log", "txt", "json", "yaml", "csv", "pdf"),
        description=(
            "Engineering field work carrier. Expected content: logs, configs, exported "
            "diagnostics, manuals. Consistent with a field engineer carrying operational data."
        ),
        typical_directories=("logs", "configs", "diagnostics", "manuals", "exports"),
        min_file_count=15,
        occupancy_ratio_warn=0.08,
    ),
    "researcher": ContextProfile(
        profile_name="researcher",
        container_name="research.vessel",
        expected_size_range=(50 * 1024 * 1024, 4 * 1024 * 1024 * 1024),
        dummy_content_types=("pdf", "txt", "csv", "json", "md", "bib"),
        description=(
            "Research material carrier. Expected content: PDFs, notes, references, exported "
            "datasets. Consistent with a researcher carrying working documents."
        ),
        typical_directories=("papers", "notes", "references", "datasets", "drafts"),
        min_file_count=25,
        occupancy_ratio_warn=0.12,
    ),
    "maintenance": ContextProfile(
        profile_name="maintenance",
        container_name="maintenance.vessel",
        expected_size_range=(10 * 1024 * 1024, 256 * 1024 * 1024),
        dummy_content_types=("log", "txt", "json", "csv", "xml"),
        description=(
            "Device maintenance carrier. Expected content: diagnostic exports, system check "
            "results, update files. Consistent with a maintenance technician."
        ),
        typical_directories=("diagnostics", "checks", "updates", "reports", "backups"),
        min_file_count=10,
        occupancy_ratio_warn=0.06,
    ),
    "archive": ContextProfile(
        profile_name="archive",
        container_name="archive.vessel",
        expected_size_range=(100 * 1024 * 1024, 8 * 1024 * 1024 * 1024),
        dummy_content_types=("pdf", "txt", "jpg", "png", "docx", "xlsx", "csv"),
        description=(
            "Long-term archive carrier. Expected content: documents, media, backups. "
            "Consistent with a general-purpose personal or work archive."
        ),
        typical_directories=("documents", "media", "backups", "exports", "misc"),
        min_file_count=30,
        occupancy_ratio_warn=0.15,
    ),
}


def get_profile(name: str) -> ContextProfile | None:
    """Return a built-in profile by name, or None if not found."""
    return BUILT_IN_PROFILES.get(name.strip().lower())


def list_profiles() -> list[str]:
    """Return sorted list of built-in profile names."""
    return sorted(BUILT_IN_PROFILES.keys())


@dataclass
class ProfileValidationResult:
    profile_name: str
    container_size_bytes: int
    dummy_size_bytes: int
    file_count: int
    occupancy_ratio: float
    extension_distribution: dict[str, int]
    warnings: list[str] = field(default_factory=list)

    @property
    def is_plausible(self) -> bool:
        return len(self.warnings) == 0


def validate_against_profile(
    *,
    profile: ContextProfile,
    container_size_bytes: int,
    dummy_size_bytes: int,
    file_count: int,
    extension_distribution: dict[str, int],
) -> ProfileValidationResult:
    """
    Validate a dummy dataset against a context profile.

    Returns a ProfileValidationResult with any plausibility warnings.
    This is advisory only — it does not modify any files.
    """
    warnings: list[str] = []

    min_bytes, max_bytes = profile.expected_size_range
    if container_size_bytes > 0:
        if container_size_bytes < min_bytes:
            warnings.append(
                f"container size {_human_bytes(container_size_bytes)} is below "
                f"expected minimum {_human_bytes(min_bytes)} for '{profile.profile_name}'"
            )
        if container_size_bytes > max_bytes:
            warnings.append(
                f"container size {_human_bytes(container_size_bytes)} exceeds "
                f"expected maximum {_human_bytes(max_bytes)} for '{profile.profile_name}'"
            )

    occupancy_ratio = 0.0
    if container_size_bytes > 0:
        occupancy_ratio = dummy_size_bytes / float(container_size_bytes)
    if container_size_bytes > 0 and occupancy_ratio < profile.occupancy_ratio_warn:
        warnings.append(
            f"occupancy ratio {occupancy_ratio:.1%} is below "
            f"warning threshold {profile.occupancy_ratio_warn:.1%} for '{profile.profile_name}'"
        )

    if file_count < profile.min_file_count:
        warnings.append(
            f"file count {file_count} is below "
            f"minimum {profile.min_file_count} for '{profile.profile_name}'"
        )

    if extension_distribution:
        expected = set(profile.dummy_content_types)
        actual = {ext.lower().lstrip(".") for ext in extension_distribution}
        unexpected = actual - expected
        if unexpected and not (actual & expected):
            warnings.append(
                f"file types {sorted(unexpected)} are not among expected types "
                f"{sorted(expected)} for '{profile.profile_name}'"
            )

    if dummy_size_bytes == 0:
        warnings.append("dummy dataset is empty — disclosure will appear trivially empty")

    return ProfileValidationResult(
        profile_name=profile.profile_name,
        container_size_bytes=container_size_bytes,
        dummy_size_bytes=dummy_size_bytes,
        file_count=file_count,
        occupancy_ratio=occupancy_ratio,
        extension_distribution=dict(extension_distribution),
        warnings=warnings,
    )


def _human_bytes(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    size = float(value)
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PiB"
