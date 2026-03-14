"""Report and plot generation for fuzzing campaign results."""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for CI / headless environments
import matplotlib.pyplot as plt

from dna_proto.evaluation.metrics import compute_metrics


def generate_report(
    results: list[dict],
    output_dir: str | Path,
) -> dict:
    """Generate summary metrics, JSON report, and plots.

    Args:
        results:    List of trial dicts from the campaign runner.
        output_dir: Directory where report files are written.

    Returns:
        Summary metrics dict.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = compute_metrics(results)

    # Write JSON summary
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)

    # Plot 1: Success rate vs mutation level
    per_level = metrics["per_level"]
    if per_level:
        levels = sorted(per_level.keys())
        rates = [per_level[lvl]["success_rate"] for lvl in levels]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(levels, rates, marker="o", linewidth=2, color="steelblue")
        ax.set_xlabel("SNP Mutations per Trial")
        ax.set_ylabel("Reconstruction Success Rate")
        ax.set_title("Fuzzy Extractor: Success Rate vs. Adversarial SNP Mutations")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.4)
        fig.tight_layout()
        fig.savefig(output_dir / "success_rate_vs_mutations.png", dpi=150)
        plt.close(fig)

    # Plot 2: FAR / FRR bar chart
    fig, ax = plt.subplots(figsize=(6, 5))
    metrics_bar = {"FRR": metrics["frr"], "FAR": metrics["far"]}
    colors = ["tomato", "steelblue"]
    bars = ax.bar(list(metrics_bar.keys()), list(metrics_bar.values()), color=colors)
    ax.set_ylabel("Rate")
    ax.set_title("False Rejection Rate (FRR) and False Acceptance Rate (FAR)")
    ax.set_ylim(0, 1.05)
    for bar, val in zip(bars, metrics_bar.values()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{val:.4f}",
            ha="center",
            va="bottom",
        )
    fig.tight_layout()
    fig.savefig(output_dir / "far_frr.png", dpi=150)
    plt.close(fig)

    return metrics


def load_jsonl(path: str | Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    results = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def save_jsonl(results: list[dict], path: str | Path) -> None:
    """Save a list of dicts as a JSONL file."""
    with open(path, "w", encoding="utf-8") as fh:
        for record in results:
            fh.write(json.dumps(record) + "\n")
