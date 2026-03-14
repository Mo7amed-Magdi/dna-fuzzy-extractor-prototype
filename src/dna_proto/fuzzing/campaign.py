"""Adversarial fuzzing campaign runner."""

from __future__ import annotations

import random
from typing import Any

from dna_proto.dna_input.schema import validate_profile
from dna_proto.fuzzy_extractor.rep import rep
from dna_proto.fuzzing.mutators import mutate_snp_substitution, mutate_str_shift
from dna_proto.kdf_keys.x25519_keys import public_key_to_bytes
from dna_proto.preprocess.vectorize import vectorize


def run_genuine_trial(
    seed_profile_dict: dict[str, Any],
    helper_data: dict,
    n_snp_mutations: int,
    n_str_mutations: int,
    rng: random.Random,
) -> dict:
    """Run a single genuine reconstruction trial with mutated biometric.

    Returns a result dict with keys:
        attempt_type, n_snp_mutations, n_str_mutations, success,
        public_key_hex (or None).
    """
    mutated = mutate_snp_substitution(seed_profile_dict, n_snp_mutations, rng)
    mutated = mutate_str_shift(mutated, n_str_mutations, max_shift=2, rng=rng)
    profile = validate_profile(mutated)
    biometric = vectorize(profile)
    _key, priv, success = rep(biometric, helper_data)
    pub_hex = None
    if success and priv is not None:
        pub_hex = public_key_to_bytes(priv.public_key()).hex()
    return {
        "attempt_type": "genuine",
        "n_snp_mutations": n_snp_mutations,
        "n_str_mutations": n_str_mutations,
        "success": success,
        "public_key_hex": pub_hex,
    }


def run_impostor_trial(
    impostor_profile_dict: dict[str, Any],
    helper_data: dict,
    impostor_id: str,
) -> dict:
    """Run a single impostor reconstruction trial.

    Returns a result dict with keys:
        attempt_type, impostor_id, success, public_key_hex (or None).
    """
    profile = validate_profile(impostor_profile_dict)
    biometric = vectorize(profile)
    _key, priv, success = rep(biometric, helper_data)
    pub_hex = None
    if success and priv is not None:
        pub_hex = public_key_to_bytes(priv.public_key()).hex()
    return {
        "attempt_type": "impostor",
        "impostor_id": impostor_id,
        "success": success,
        "public_key_hex": pub_hex,
    }


def run_campaign(
    seed_profile_dict: dict[str, Any],
    helper_data: dict,
    impostor_dicts: list[dict[str, Any]],
    mutation_levels: list[int],
    n_trials_per_level: int = 200,
    seed: int = 42,
) -> list[dict]:
    """Run a full adversarial fuzzing campaign.

    For each mutation level (number of SNP mutations), run n_trials_per_level
    genuine trials with mutated biometrics, then run impostor trials.

    Args:
        seed_profile_dict:    Base DNA profile dict for genuine trials.
        helper_data:          Enrollment helper data produced by gen().
        impostor_dicts:       List of other subjects' profile dicts.
        mutation_levels:      List of SNP mutation counts to test (e.g. [0,1,2,4,8]).
        n_trials_per_level:   Number of genuine trials per mutation level.
        seed:                 RNG seed for reproducibility.

    Returns:
        List of result dicts (one per trial).
    """
    results: list[dict] = []
    rng = random.Random(seed)

    for level in mutation_levels:
        for _ in range(n_trials_per_level):
            result = run_genuine_trial(
                seed_profile_dict=seed_profile_dict,
                helper_data=helper_data,
                n_snp_mutations=level,
                n_str_mutations=0,
                rng=rng,
            )
            results.append(result)

    for impostor_dict in impostor_dicts:
        imp_id = impostor_dict.get("subject_id", "unknown")
        result = run_impostor_trial(impostor_dict, helper_data, imp_id)
        results.append(result)

    return results
