"""Experiment controller: end-to-end automated testing cycle.

Runs:
1. Enrollment of the base profile.
2. Fuzz campaign across configured noise levels.
3. Impostor attacks using other profiles.
4. Evaluation metrics computation.
5. Report generation (summary JSON + plots).

All intermediate artifacts are written to ``out_dir``.
Raw DNA / encoded vectors are NEVER written to disk.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..dna_input.loader import load_profile
from ..dna_input.schema import load_marker_catalogue, validate_profile
from ..evaluation.metrics import compute_metrics
from ..evaluation.report import generate_plots, save_summary
from ..fuzzy_extractor.gen import gen, save_enrollment
from ..fuzzing.campaign import run_campaign
from ..preprocess.vectorize import profile_to_bytes, catalogue_fingerprint


def run_experiment(
    base_profile_path: str | Path,
    *,
    catalogue_path: str | Path | None = None,
    impostor_profile_paths: list[str | Path] | None = None,
    out_dir: str | Path = "results",
    snp_rates: list[float] | None = None,
    str_shifts: list[int] | None = None,
    bit_flip_rates: list[float] | None = None,
    n_trials: int = 100,
    seed: int | None = 42,
    tolerance: int = 0,
) -> dict[str, Any]:
    """Run the complete experiment pipeline.

    Parameters
    ----------
    base_profile_path:
        Path to the enrolled subject's profile JSON/CSV.
    catalogue_path:
        Path to the marker catalogue JSON.  Uses default if *None*.
    impostor_profile_paths:
        Paths to other subjects' profiles for FAR testing.
    out_dir:
        Directory to write enrollment artifact, JSONL log, summary, and plots.
    snp_rates, str_shifts, bit_flip_rates:
        Noise levels for the fuzz campaign.
    n_trials:
        Number of trials per noise level.
    seed:
        RNG seed for reproducibility.
    tolerance:
        Informational tolerance parameter stored in enrollment artifacts.

    Returns
    -------
    Metrics dict.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Load catalogue and base profile ────────────────────────────────────
    catalogue = load_marker_catalogue(catalogue_path)
    base_profile = load_profile(base_profile_path)
    validate_profile(base_profile, catalogue)
    subject_id = base_profile.get("subject_id", "unknown")

    cat_fp = catalogue_fingerprint(catalogue)

    # ── Enrollment (Gen) ───────────────────────────────────────────────────
    w = profile_to_bytes(base_profile, catalogue)
    key_material, enrollment = gen(w, cat_fp, tolerance=tolerance)
    del w  # do not keep encoded vector in memory longer than needed

    enrollment_path = out_dir / f"enrollment_{subject_id}.json"
    save_enrollment(enrollment, enrollment_path)

    # Write a metadata file (does NOT contain raw DNA or encoded vectors)
    meta = {
        "subject_id": subject_id,
        "catalogue_fp": cat_fp,
        "n_bytes": enrollment["n_bytes"],
        "tolerance": tolerance,
        "enrolled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(out_dir / f"meta_{subject_id}.json", "w") as fh:
        json.dump(meta, fh, indent=2)

    # ── Load impostor profiles ─────────────────────────────────────────────
    impostor_profiles: list[dict[str, Any]] = []
    for imp_path in (impostor_profile_paths or []):
        try:
            imp = load_profile(imp_path)
            validate_profile(imp, catalogue)
            impostor_profiles.append(imp)
        except (ValueError, FileNotFoundError) as exc:
            print(f"Warning: skipping impostor profile {imp_path}: {exc}")

    # ── Fuzz campaign ──────────────────────────────────────────────────────
    results_path = out_dir / f"campaign_{subject_id}.jsonl"
    if results_path.exists():
        results_path.unlink()  # start fresh

    results = run_campaign(
        base_profile,
        enrollment,
        catalogue,
        snp_rates=snp_rates,
        str_shifts=str_shifts,
        n_trials=n_trials,
        bit_flip_rates=bit_flip_rates,
        seed=seed,
        impostor_profiles=impostor_profiles,
        out_path=results_path,
    )

    # ── Metrics ────────────────────────────────────────────────────────────
    metrics = compute_metrics(results)
    metrics["subject_id"] = subject_id
    metrics["enrollment_path"] = str(enrollment_path)

    summary_path = out_dir / f"summary_{subject_id}.json"
    save_summary(metrics, summary_path)

    # ── Plots ──────────────────────────────────────────────────────────────
    plots_dir = out_dir / "plots"
    plot_files = generate_plots(metrics, plots_dir)

    metrics["summary_path"] = str(summary_path)
    metrics["plot_files"] = [str(p) for p in plot_files]

    return metrics
