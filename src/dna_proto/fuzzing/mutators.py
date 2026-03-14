"""Biometric mutation strategies for adversarial fuzzing."""

from __future__ import annotations

import copy
import random
from typing import Any

from dna_proto.dna_input.schema import STR_MAX, STR_MIN, VALID_BASES

BASES = sorted(VALID_BASES)  # ['A', 'C', 'G', 'T']


def mutate_snp_substitution(
    profile: dict[str, Any],
    n_mutations: int,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Replace exactly n_mutations SNP bases with a different random base.

    Args:
        profile:     DNA profile dict (snps, strs, subject_id).
        n_mutations: Exact number of SNP positions to mutate.
        rng:         Optional seeded Random instance for reproducibility.

    Returns:
        A deep copy of the profile with mutated SNPs.
    """
    rng = rng or random.Random()
    profile = copy.deepcopy(profile)
    snp_keys = list(profile["snps"].keys())
    targets = rng.sample(snp_keys, min(n_mutations, len(snp_keys)))
    for key in targets:
        current = profile["snps"][key]
        others = [b for b in BASES if b != current]
        profile["snps"][key] = rng.choice(others)
    return profile


def mutate_str_shift(
    profile: dict[str, Any],
    n_mutations: int,
    max_shift: int = 2,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Shift exactly n_mutations STR repeat counts by a random amount in [-max_shift, max_shift].

    Values are clamped to [STR_MIN, STR_MAX].
    """
    rng = rng or random.Random()
    profile = copy.deepcopy(profile)
    str_keys = list(profile["strs"].keys())
    targets = rng.sample(str_keys, min(n_mutations, len(str_keys)))
    for key in targets:
        current = profile["strs"][key]
        shifts = [d for d in range(-max_shift, max_shift + 1) if d != 0]
        delta = rng.choice(shifts)
        profile["strs"][key] = max(STR_MIN, min(STR_MAX, current + delta))
    return profile


def mutate_bit_flip(
    biometric: bytes,
    n_flips: int,
    rng: random.Random | None = None,
) -> bytes:
    """Flip exactly n_flips random bits in the biometric byte string."""
    rng = rng or random.Random()
    n_bits = len(biometric) * 8
    positions = rng.sample(range(n_bits), min(n_flips, n_bits))
    buf = bytearray(biometric)
    for pos in positions:
        buf[pos >> 3] ^= 1 << (7 - (pos & 7))
    return bytes(buf)


def mutate_boundary_str(
    profile: dict[str, Any],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Set a random STR to a boundary value (STR_MIN or STR_MAX)."""
    rng = rng or random.Random()
    profile = copy.deepcopy(profile)
    if not profile["strs"]:
        return profile
    key = rng.choice(list(profile["strs"].keys()))
    profile["strs"][key] = rng.choice([STR_MIN, STR_MAX])
    return profile


def mutate_realistic(
    profile: dict[str, Any],
    snp_rate: float = 0.01,
    str_rate: float = 0.05,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Apply statistically realistic mutations.

    SNPs: transition bias (A↔G, C↔T) at snp_rate per locus.
    STRs: ±1 shift at str_rate per locus.
    """
    rng = rng or random.Random()
    profile = copy.deepcopy(profile)

    transition_map = {"A": "G", "G": "A", "C": "T", "T": "C"}
    transversion_map = {"A": ["C", "T"], "G": ["C", "T"], "C": ["A", "G"], "T": ["A", "G"]}

    for key in profile["snps"]:
        if rng.random() < snp_rate:
            base = profile["snps"][key]
            # 80% transition, 20% transversion
            if rng.random() < 0.8:
                profile["snps"][key] = transition_map[base]
            else:
                profile["snps"][key] = rng.choice(transversion_map[base])

    for key in profile["strs"]:
        if rng.random() < str_rate:
            current = profile["strs"][key]
            delta = rng.choice([-1, 1])
            profile["strs"][key] = max(STR_MIN, min(STR_MAX, current + delta))

    return profile
