"""Fuzzing campaign: systematic mutation + reconstruction attempts.

Each campaign takes a base profile, applies mutations across a range of noise
levels, runs Rep() for each mutated sample, and logs the outcome to a JSONL
file.  Impostor tests use unrelated profiles.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

from ..dna_input.schema import validate_profile
from ..fuzzy_extractor.rep import rep, ReconstructionError
from ..preprocess.vectorize import profile_to_bytes, hamming_distance
from .mutators import composite_mutate, bit_flip_vector


def run_campaign(
    base_profile: dict[str, Any],
    enrollment: dict,
    catalogue: dict[str, Any],
    *,
    snp_rates: list[float] | None = None,
    str_shifts: list[int] | None = None,
    n_trials: int = 100,
    bit_flip_rates: list[float] | None = None,
    seed: int | None = None,
    impostor_profiles: list[dict[str, Any]] | None = None,
    out_path: Path | str | None = None,
) -> list[dict]:
    """Run a fuzz campaign against an enrollment artifact.

    Parameters
    ----------
    base_profile:
        The genuine enrolled profile (used as the base for mutations).
    enrollment:
        Enrollment artifact dict from ``gen()``.
    catalogue:
        Canonical marker catalogue.
    snp_rates:
        List of SNP mutation rates to sweep.  Default: [0, 0.01, 0.05, 0.10].
    str_shifts:
        List of STR shift magnitudes to sweep.  Default: [0, 1, 2, 3].
    n_trials:
        Number of independent mutation trials per (snp_rate, str_shift) pair.
    bit_flip_rates:
        Optional list of bit-flip rates to apply post-encoding.
    seed:
        Random seed for reproducibility.
    impostor_profiles:
        List of unrelated profiles for FAR measurement.
    out_path:
        If given, append each result as a JSONL line to this file.

    Returns
    -------
    List of result dicts (one per attempt).
    """
    if snp_rates is None:
        snp_rates = [0.0, 0.01, 0.02, 0.05, 0.10, 0.20]
    if str_shifts is None:
        str_shifts = [0, 1, 2, 3]
    if bit_flip_rates is None:
        bit_flip_rates = []

    rng = random.Random(seed)
    results: list[dict] = []
    w_base = profile_to_bytes(base_profile, catalogue)

    def _record(result: dict) -> None:
        results.append(result)
        if out_path:
            with open(out_path, "a") as fh:
                fh.write(json.dumps(result) + "\n")

    # ── Genuine fuzz trials ────────────────────────────────────────────────
    for snp_rate in snp_rates:
        for str_shift_mag in str_shifts:
            for trial in range(n_trials):
                trial_seed = rng.randint(0, 2**31)
                trial_rng = random.Random(trial_seed)
                mutated = composite_mutate(
                    base_profile,
                    catalogue,
                    snp_rate=snp_rate,
                    str_shift_mag=str_shift_mag,
                    rng=trial_rng,
                )
                try:
                    validate_profile(mutated, catalogue)
                except ValueError:
                    # Mutation produced an invalid profile (e.g., STR out of range);
                    # skip this trial.
                    continue

                w_prime = profile_to_bytes(mutated, catalogue)
                hd = hamming_distance(w_base, w_prime)

                success = False
                try:
                    rep(w_prime, enrollment)
                    success = True
                except ReconstructionError:
                    pass

                _record(
                    {
                        "type": "genuine",
                        "snp_rate": snp_rate,
                        "str_shift_mag": str_shift_mag,
                        "trial": trial,
                        "hamming_distance": hd,
                        "success": success,
                        "ts": time.time(),
                    }
                )

    # ── Bit-flip trials (post-encoding) ────────────────────────────────────
    for flip_rate in bit_flip_rates:
        for trial in range(n_trials):
            w_flipped = bit_flip_vector(w_base, flip_rate, rng=rng)
            hd = hamming_distance(w_base, w_flipped)
            success = False
            try:
                rep(w_flipped, enrollment)
                success = True
            except ReconstructionError:
                pass

            _record(
                {
                    "type": "bit_flip",
                    "flip_rate": flip_rate,
                    "trial": trial,
                    "hamming_distance": hd,
                    "success": success,
                    "ts": time.time(),
                }
            )

    # ── Impostor trials (FAR) ──────────────────────────────────────────────
    for imp_profile in (impostor_profiles or []):
        try:
            validate_profile(imp_profile, catalogue)
        except ValueError:
            continue
        w_imp = profile_to_bytes(imp_profile, catalogue)
        hd = hamming_distance(w_base, w_imp)
        success = False
        try:
            rep(w_imp, enrollment)
            success = True
        except ReconstructionError:
            pass

        _record(
            {
                "type": "impostor",
                "subject_id": imp_profile.get("subject_id", "unknown"),
                "hamming_distance": hd,
                "success": success,
                "ts": time.time(),
            }
        )

    return results


def load_results(path: Path | str) -> list[dict]:
    """Load a JSONL results file produced by ``run_campaign``."""
    results = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results
