"""End-to-end experiment orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dna_proto.dna_input.schema import validate_profile
from dna_proto.evaluation.report import generate_report, save_jsonl
from dna_proto.fuzzy_extractor.gen import gen
from dna_proto.fuzzing.campaign import run_campaign
from dna_proto.preprocess.vectorize import vectorize


def run_experiment(
    seed_profile_dict: dict[str, Any],
    impostor_dicts: list[dict[str, Any]],
    mutation_levels: list[int] | None = None,
    n_trials_per_level: int = 200,
    output_dir: str | Path = "results",
    rng_seed: int = 42,
) -> dict:
    """Run a complete enrollment → fuzzing → evaluation experiment.

    Args:
        seed_profile_dict:  DNA profile dict for the enrolled subject.
        impostor_dicts:     List of other subjects' profile dicts.
        mutation_levels:    SNP mutation counts to test (default: [0,1,2,4,8,16]).
        n_trials_per_level: Genuine trials per mutation level.
        output_dir:         Directory for output files.
        rng_seed:           RNG seed for reproducibility.

    Returns:
        Summary metrics dict.
    """
    if mutation_levels is None:
        mutation_levels = [0, 1, 2, 4, 8, 16]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Enroll
    profile = validate_profile(seed_profile_dict)
    biometric = vectorize(profile)
    _secret, helper_data = gen(biometric)

    # Save enrollment helper data
    enrollment_path = output_dir / "enrollment.json"
    with open(enrollment_path, "w", encoding="utf-8") as fh:
        json.dump(helper_data, fh, indent=2)

    # 2. Run campaign
    results = run_campaign(
        seed_profile_dict=seed_profile_dict,
        helper_data=helper_data,
        impostor_dicts=impostor_dicts,
        mutation_levels=mutation_levels,
        n_trials_per_level=n_trials_per_level,
        seed=rng_seed,
    )

    # 3. Save raw results
    results_path = output_dir / "campaign.jsonl"
    save_jsonl(results, results_path)

    # 4. Generate report + plots
    metrics = generate_report(results, output_dir)

    return metrics
