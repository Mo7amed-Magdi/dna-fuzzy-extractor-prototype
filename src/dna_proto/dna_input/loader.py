"""Loaders for JSON and CSV DNA marker profile files."""

from __future__ import annotations

import json
from pathlib import Path

from dna_proto.dna_input.schema import DNAProfile, profile_from_csv_text, validate_profile


def load_json(path: str | Path) -> DNAProfile:
    """Load a DNA profile from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return validate_profile(raw)


def load_csv(path: str | Path) -> DNAProfile:
    """Load a DNA profile from a CSV file (long format).

    Expected columns: subject_id, marker_type, marker_id, value
    """
    text = Path(path).read_text(encoding="utf-8")
    return profile_from_csv_text(text)


def load_profile(path: str | Path) -> DNAProfile:
    """Auto-detect format (JSON or CSV) and load a DNA profile."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".json",):
        return load_json(p)
    elif suffix in (".csv",):
        return load_csv(p)
    else:
        raise ValueError(f"Unsupported file extension {suffix!r}; use .json or .csv")
