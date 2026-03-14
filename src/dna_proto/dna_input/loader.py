"""DNA profile loader supporting JSON and CSV formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def load_profile(path: Path | str) -> dict[str, Any]:
    """Load a DNA profile from a JSON or CSV file.

    JSON format (preferred)::

        {
            "subject_id": "S1",
            "snps": {"rs1": "A", "rs2": "G"},
            "strs": {"D3S1358": 15, "vWA": 17}
        }

    CSV format (long-form rows)::

        subject_id,marker_type,marker_id,value
        S1,SNP,rs1,A
        S1,STR,D3S1358,15

    Parameters
    ----------
    path:
        Path to a ``.json`` or ``.csv`` file.

    Returns
    -------
    dict with keys ``subject_id``, ``snps``, and ``strs``.
    """
    resolved = Path(path)
    suffix = resolved.suffix.lower()
    if suffix == ".json":
        return _load_json(resolved)
    if suffix == ".csv":
        return _load_csv(resolved)
    raise ValueError(f"Unsupported file format '{suffix}'. Use .json or .csv.")


def _load_json(path: Path) -> dict[str, Any]:
    with open(path) as fh:
        data = json.load(fh)
    # Normalise: SNP values to uppercase
    snps = {k: str(v).upper() for k, v in data.get("snps", {}).items()}
    strs = {k: int(v) for k, v in data.get("strs", {}).items()}
    return {
        "subject_id": data.get("subject_id", path.stem),
        "snps": snps,
        "strs": strs,
    }


def _load_csv(path: Path) -> dict[str, Any]:
    snps: dict[str, str] = {}
    strs: dict[str, int] = {}
    subject_id: str | None = None

    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if subject_id is None:
                subject_id = row.get("subject_id", path.stem)
            mtype = row["marker_type"].upper()
            mid = row["marker_id"]
            val = row["value"]
            if mtype == "SNP":
                snps[mid] = val.upper()
            elif mtype == "STR":
                strs[mid] = int(val)
            else:
                raise ValueError(f"Unknown marker_type '{mtype}' in CSV row: {row}")

    return {
        "subject_id": subject_id or path.stem,
        "snps": snps,
        "strs": strs,
    }
