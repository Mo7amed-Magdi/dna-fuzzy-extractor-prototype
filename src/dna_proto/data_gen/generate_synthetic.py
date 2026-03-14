"""Generate synthetic DNA marker profiles for testing and demonstration.

Produces:
    data/synthetic_markers.json  - marker definitions (SNP IDs + STR IDs)
    data/synthetic_profiles/subject_XXX.json  - individual subject profiles

All data is entirely synthetic / randomly generated.
No real human DNA is used or implied.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from dna_proto.dna_input.schema import STR_MAX, STR_MIN, VALID_BASES
from dna_proto.preprocess.vectorize import N_SNPS, N_STRS

BASES = sorted(VALID_BASES)
_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = _REPO_ROOT / "data"
PROFILES_DIR = DATA_DIR / "synthetic_profiles"


def _make_marker_definitions() -> dict:
    """Create the ordered list of SNP and STR marker IDs."""
    snp_ids = [f"rs{i:04d}" for i in range(1, N_SNPS + 1)]
    str_ids = [f"str_{i:03d}" for i in range(1, N_STRS + 1)]
    return {"snp_ids": snp_ids, "str_ids": str_ids}


def _generate_subject(
    subject_id: str,
    snp_ids: list[str],
    str_ids: list[str],
    rng: random.Random,
    base_snps: dict[str, str] | None = None,
    base_strs: dict[str, int] | None = None,
    relatedness: float = 0.0,
) -> dict:
    """Generate a random DNA profile for one synthetic subject.

    Args:
        subject_id:  String identifier.
        snp_ids:     Ordered list of SNP marker IDs.
        str_ids:     Ordered list of STR marker IDs.
        rng:         Seeded Random instance.
        base_snps:   Optional base profile SNPs (for related subjects).
        base_strs:   Optional base profile STRs (for related subjects).
        relatedness: Fraction of markers inherited from the base profile (0–1).
    """
    snps: dict[str, str] = {}
    for sid in snp_ids:
        if base_snps and rng.random() < relatedness:
            snps[sid] = base_snps[sid]
        else:
            snps[sid] = rng.choice(BASES)

    strs: dict[str, int] = {}
    for sid in str_ids:
        if base_strs and rng.random() < relatedness:
            strs[sid] = base_strs[sid]
        else:
            strs[sid] = rng.randint(STR_MIN, STR_MAX)

    return {
        "subject_id": subject_id,
        "snps": snps,
        "strs": strs,
    }


def generate_profiles(
    n_subjects: int = 10,
    seed: int = 1234,
    output_dir: Path | None = None,
    markers_output: Path | None = None,
) -> tuple[dict, list[dict]]:
    """Generate synthetic marker definitions and subject profiles.

    Args:
        n_subjects:      Number of independent subjects to generate.
        seed:            RNG seed for reproducibility.
        output_dir:      Where to write subject JSON files (None = don't write).
        markers_output:  Where to write markers JSON (None = don't write).

    Returns:
        (markers_dict, list_of_profile_dicts)
    """
    rng = random.Random(seed)
    markers = _make_marker_definitions()

    profiles = []
    for i in range(1, n_subjects + 1):
        subject_id = f"subject_{i:03d}"
        profile = _generate_subject(
            subject_id=subject_id,
            snp_ids=markers["snp_ids"],
            str_ids=markers["str_ids"],
            rng=rng,
        )
        profiles.append(profile)

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for profile in profiles:
            sid = profile["subject_id"]
            path = output_dir / f"{sid}.json"
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(profile, fh, indent=2)

    if markers_output is not None:
        markers_output = Path(markers_output)
        markers_output.parent.mkdir(parents=True, exist_ok=True)
        with open(markers_output, "w", encoding="utf-8") as fh:
            json.dump(markers, fh, indent=2)

    return markers, profiles


if __name__ == "__main__":
    print("Generating synthetic DNA marker definitions and profiles …")
    markers, profiles = generate_profiles(
        n_subjects=10,
        seed=1234,
        output_dir=PROFILES_DIR,
        markers_output=DATA_DIR / "synthetic_markers.json",
    )
    print(f"  Wrote {len(profiles)} profiles to {PROFILES_DIR}/")
    print(f"  Wrote marker definitions to {DATA_DIR / 'synthetic_markers.json'}")
