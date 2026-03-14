"""Schema definitions and validation for DNA marker profiles."""

from __future__ import annotations

import csv
import io
from typing import Any

VALID_BASES: frozenset[str] = frozenset("ACGT")
STR_MIN: int = 5
STR_MAX: int = 30


class DNAProfile:
    """Validated DNA marker profile."""

    def __init__(
        self,
        subject_id: str,
        snps: dict[str, str],
        strs: dict[str, int],
    ) -> None:
        self.subject_id = subject_id
        self.snps = snps
        self.strs = strs

    def __repr__(self) -> str:
        return (
            f"DNAProfile(subject_id={self.subject_id!r}, "
            f"n_snps={len(self.snps)}, n_strs={len(self.strs)})"
        )


def validate_profile(raw: dict[str, Any]) -> DNAProfile:
    """Validate a raw dict and return a DNAProfile.

    Raises ValueError on invalid data.
    """
    subject_id = str(raw.get("subject_id", "unknown"))

    raw_snps = raw.get("snps", {})
    if not isinstance(raw_snps, dict):
        raise ValueError("'snps' must be a dict mapping marker ID to nucleotide")
    snps: dict[str, str] = {}
    for marker_id, value in raw_snps.items():
        if not isinstance(value, str) or value.upper() not in VALID_BASES:
            raise ValueError(
                f"SNP '{marker_id}': value {value!r} must be one of A, C, G, T"
            )
        snps[str(marker_id)] = value.upper()

    raw_strs = raw.get("strs", {})
    if not isinstance(raw_strs, dict):
        raise ValueError("'strs' must be a dict mapping marker ID to repeat count")
    strs: dict[str, int] = {}
    for marker_id, value in raw_strs.items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"STR '{marker_id}': value {value!r} must be an integer"
            )
        if not (STR_MIN <= count <= STR_MAX):
            raise ValueError(
                f"STR '{marker_id}': count {count} out of range [{STR_MIN}, {STR_MAX}]"
            )
        strs[str(marker_id)] = count

    return DNAProfile(subject_id=subject_id, snps=snps, strs=strs)


def profile_from_csv_text(text: str) -> DNAProfile:
    """Parse a CSV string in long format into a DNAProfile.

    Expected columns: subject_id, marker_type, marker_id, value
    """
    reader = csv.DictReader(io.StringIO(text))
    subject_id: str | None = None
    snps: dict[str, str] = {}
    strs: dict[str, int] = {}

    for row in reader:
        sid = row.get("subject_id", "").strip()
        if subject_id is None:
            subject_id = sid
        elif sid and sid != subject_id:
            raise ValueError(
                f"CSV contains multiple subject IDs: {subject_id!r} and {sid!r}"
            )
        marker_type = row.get("marker_type", "").strip().upper()
        marker_id = row.get("marker_id", "").strip()
        value = row.get("value", "").strip()

        if marker_type == "SNP":
            if value.upper() not in VALID_BASES:
                raise ValueError(f"SNP '{marker_id}': invalid base {value!r}")
            snps[marker_id] = value.upper()
        elif marker_type == "STR":
            try:
                count = int(value)
            except ValueError:
                raise ValueError(f"STR '{marker_id}': non-integer value {value!r}")
            if not (STR_MIN <= count <= STR_MAX):
                raise ValueError(
                    f"STR '{marker_id}': count {count} out of range [{STR_MIN}, {STR_MAX}]"
                )
            strs[marker_id] = count
        else:
            raise ValueError(f"Unknown marker_type {marker_type!r} for marker {marker_id!r}")

    return DNAProfile(
        subject_id=subject_id or "unknown",
        snps=snps,
        strs=strs,
    )
