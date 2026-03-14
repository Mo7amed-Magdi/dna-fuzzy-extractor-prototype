"""Adversarial mutation strategies for DNA profiles.

Mutation strategies:
- snp_substitution: randomly change SNP bases (biased toward transitions).
- str_shift: shift STR repeat counts by ±d.
- bit_flip: flip random bits in the encoded vector post-encoding.
- boundary: push STR values to min/max boundary.
- composite: apply multiple strategies simultaneously.
"""

from __future__ import annotations

import copy
import random
from typing import Any

from ..dna_input.schema import VALID_BASES

# Transition mutations (biologically more common): A↔G, C↔T
_TRANSITIONS: dict[str, str] = {"A": "G", "G": "A", "C": "T", "T": "C"}
_ALL_BASES = sorted(VALID_BASES)


def snp_substitution(
    profile: dict[str, Any],
    rate: float,
    *,
    transition_bias: float = 0.7,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Mutate SNP markers by random base substitution.

    Parameters
    ----------
    profile:
        Source profile dict.
    rate:
        Fraction of SNP markers to mutate (0.0 – 1.0).
    transition_bias:
        Probability that a mutation is a transition (A↔G or C↔T) rather than
        a transversion.  Mirrors biological mutation statistics.
    rng:
        Optional seeded :class:`random.Random` instance for reproducibility.

    Returns
    -------
    New profile dict with mutated SNP values.
    """
    if rng is None:
        rng = random.Random()
    mutated = copy.deepcopy(profile)
    snps: dict[str, str] = mutated["snps"]
    marker_ids = list(snps.keys())
    n_mutate = max(0, int(round(len(marker_ids) * rate)))
    targets = rng.sample(marker_ids, min(n_mutate, len(marker_ids)))
    for mid in targets:
        original = snps[mid]
        if rng.random() < transition_bias and original in _TRANSITIONS:
            snps[mid] = _TRANSITIONS[original]
        else:
            choices = [b for b in _ALL_BASES if b != original]
            snps[mid] = rng.choice(choices)
    return mutated


def str_shift(
    profile: dict[str, Any],
    catalogue: dict[str, Any],
    shift_magnitude: int,
    *,
    rate: float = 1.0,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Shift STR repeat counts by up to ±shift_magnitude.

    Parameters
    ----------
    profile:
        Source profile dict.
    catalogue:
        Marker catalogue (for min/max bounds).
    shift_magnitude:
        Maximum absolute shift applied to each STR.
    rate:
        Fraction of STR markers to shift.
    rng:
        Optional seeded RNG.

    Returns
    -------
    New profile with shifted (and clamped) STR values.
    """
    if rng is None:
        rng = random.Random()
    mutated = copy.deepcopy(profile)
    str_bounds = {e["id"]: (e["min"], e["max"]) for e in catalogue["str_markers"]}
    marker_ids = list(mutated["strs"].keys())
    n_mutate = max(0, int(round(len(marker_ids) * rate)))
    targets = rng.sample(marker_ids, min(n_mutate, len(marker_ids)))
    for mid in targets:
        lo, hi = str_bounds[mid]
        delta = rng.randint(-shift_magnitude, shift_magnitude)
        mutated["strs"][mid] = max(lo, min(hi, mutated["strs"][mid] + delta))
    return mutated


def boundary_test(
    profile: dict[str, Any],
    catalogue: dict[str, Any],
    *,
    push_to: str = "both",
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Push STR values to their min/max boundary.

    Parameters
    ----------
    push_to:
        ``"min"``, ``"max"``, or ``"both"`` (random per marker).
    """
    if rng is None:
        rng = random.Random()
    mutated = copy.deepcopy(profile)
    for entry in catalogue["str_markers"]:
        mid = entry["id"]
        if push_to == "min":
            mutated["strs"][mid] = entry["min"]
        elif push_to == "max":
            mutated["strs"][mid] = entry["max"]
        else:
            mutated["strs"][mid] = rng.choice([entry["min"], entry["max"]])
    return mutated


def bit_flip_vector(
    w: bytes,
    rate: float,
    *,
    rng: random.Random | None = None,
) -> bytes:
    """Flip bits in an encoded biometric byte vector.

    This operates AFTER encoding, directly on the byte vector.  Use to test
    the fuzzy extractor layer independently of the encoding stage.

    Parameters
    ----------
    w:
        Encoded biometric vector.
    rate:
        Fraction of bits to flip (0.0 – 1.0).
    rng:
        Optional seeded RNG.

    Returns
    -------
    New bytes with flipped bits.
    """
    if rng is None:
        rng = random.Random()
    total_bits = len(w) * 8
    n_flip = max(0, int(round(total_bits * rate)))
    positions = rng.sample(range(total_bits), min(n_flip, total_bits))
    arr = bytearray(w)
    for pos in positions:
        byte_idx = pos // 8
        bit_idx = 7 - (pos % 8)
        arr[byte_idx] ^= 1 << bit_idx
    return bytes(arr)


def composite_mutate(
    profile: dict[str, Any],
    catalogue: dict[str, Any],
    *,
    snp_rate: float = 0.0,
    str_shift_mag: int = 0,
    str_rate: float = 1.0,
    transition_bias: float = 0.7,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Apply SNP substitution and STR shift together.

    Parameters
    ----------
    snp_rate:
        Fraction of SNPs to mutate.
    str_shift_mag:
        Maximum STR shift magnitude (0 = no shift).
    str_rate:
        Fraction of STR markers to shift.
    """
    if rng is None:
        rng = random.Random()
    mutated = profile
    if snp_rate > 0:
        mutated = snp_substitution(
            mutated, snp_rate, transition_bias=transition_bias, rng=rng
        )
    if str_shift_mag > 0:
        mutated = str_shift(
            mutated, catalogue, str_shift_mag, rate=str_rate, rng=rng
        )
    return mutated
