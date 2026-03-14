"""Marker schema definitions and validation for DNA input."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Valid nucleotide bases for SNP markers
VALID_BASES: frozenset[str] = frozenset({"A", "C", "G", "T"})

# Default synthetic marker catalogue shipped with the package
_DEFAULT_MARKERS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "synthetic_markers.json"


def load_marker_catalogue(path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate the canonical marker catalogue.

    The catalogue defines the ordered list of SNP and STR markers used for
    encoding.  Order is canonical: encoding is deterministic across profiles.

    Parameters
    ----------
    path:
        Path to a JSON file with keys ``snp_markers`` (list of str) and
        ``str_markers`` (list of dicts with keys ``id``, ``min``, ``max``,
        ``n_bits``).  If *None* the default catalogue in ``data/`` is used.

    Returns
    -------
    dict with keys ``snp_markers`` and ``str_markers``.
    """
    resolved = Path(path) if path else _DEFAULT_MARKERS_PATH
    with open(resolved) as fh:
        catalogue = json.load(fh)
    _validate_catalogue(catalogue)
    return catalogue


def _validate_catalogue(catalogue: dict[str, Any]) -> None:
    if "snp_markers" not in catalogue:
        raise ValueError("Marker catalogue missing 'snp_markers'")
    if "str_markers" not in catalogue:
        raise ValueError("Marker catalogue missing 'str_markers'")
    if not isinstance(catalogue["snp_markers"], list) or not catalogue["snp_markers"]:
        raise ValueError("'snp_markers' must be a non-empty list")
    for entry in catalogue["str_markers"]:
        for key in ("id", "min", "max", "n_bits"):
            if key not in entry:
                raise ValueError(f"STR marker entry missing key '{key}': {entry}")
        if entry["min"] >= entry["max"]:
            raise ValueError(f"STR marker min >= max: {entry}")
        if entry["n_bits"] < 1 or entry["n_bits"] > 16:
            raise ValueError(f"STR n_bits out of range [1,16]: {entry}")


def validate_profile(
    profile: dict[str, Any],
    catalogue: dict[str, Any],
) -> None:
    """Validate a subject profile against the canonical marker catalogue.

    Raises
    ------
    ValueError
        If any marker is missing, or has an invalid value.
    """
    snp_ids: list[str] = catalogue["snp_markers"]
    str_entries: list[dict[str, Any]] = catalogue["str_markers"]

    profile_snps: dict[str, str] = profile.get("snps", {})
    profile_strs: dict[str, int] = profile.get("strs", {})

    # Validate SNPs
    for sid in snp_ids:
        if sid not in profile_snps:
            raise ValueError(f"Missing SNP marker '{sid}' in profile")
        val = profile_snps[sid]
        if val not in VALID_BASES:
            raise ValueError(
                f"SNP marker '{sid}' has invalid value '{val}'. Must be one of {sorted(VALID_BASES)}."
            )

    # Validate STRs
    str_lookup = {e["id"]: e for e in str_entries}
    for entry in str_entries:
        sid = entry["id"]
        if sid not in profile_strs:
            raise ValueError(f"Missing STR marker '{sid}' in profile")
        val = profile_strs[sid]
        if not isinstance(val, int):
            raise ValueError(f"STR marker '{sid}' value must be an integer, got {type(val).__name__}")
        if val < entry["min"] or val > entry["max"]:
            raise ValueError(
                f"STR marker '{sid}' value {val} out of range [{entry['min']}, {entry['max']}]"
            )
    # Unused in lookup but kept for completeness
    del str_lookup
