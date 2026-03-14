"""Report generation: summary JSON + plots.

Generates:
- A JSON summary file with all metrics.
- A PNG plot of success rate vs SNP mutation rate.
- A PNG plot of success rate vs STR shift magnitude.
- A PNG plot of success rate vs bit-flip rate (if applicable).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_summary(metrics: dict[str, Any], path: Path | str) -> None:
    """Save a metrics dict to a JSON summary file."""
    with open(path, "w") as fh:
        json.dump(metrics, fh, indent=2)


def generate_plots(metrics: dict[str, Any], out_dir: Path | str) -> list[Path]:
    """Generate PNG plots from metrics.  Returns list of created file paths."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    # ── Success rate vs SNP mutation rate ───────────────────────────────────
    snp_data = metrics.get("by_snp_rate", {})
    if snp_data:
        rates = sorted(snp_data.keys())
        successes = [snp_data[r]["success_rate"] for r in rates]
        frrs = [snp_data[r]["frr"] for r in rates]

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([r * 100 for r in rates], successes, "o-", label="Success rate", color="steelblue")
        ax.plot([r * 100 for r in rates], frrs, "s--", label="FRR", color="tomato")
        ax.set_xlabel("SNP mutation rate (%)")
        ax.set_ylabel("Rate")
        ax.set_title("Reconstruction success vs SNP mutation rate")
        ax.legend()
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        p = out_dir / "snp_mutation_rate.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        created.append(p)

    # ── Success rate vs STR shift magnitude ────────────────────────────────
    str_data = metrics.get("by_str_shift", {})
    if str_data:
        shifts = sorted(str_data.keys())
        successes = [str_data[s]["success_rate"] for s in shifts]
        frrs = [str_data[s]["frr"] for s in shifts]

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(shifts, successes, "o-", label="Success rate", color="steelblue")
        ax.plot(shifts, frrs, "s--", label="FRR", color="tomato")
        ax.set_xlabel("STR shift magnitude (repeats)")
        ax.set_ylabel("Rate")
        ax.set_title("Reconstruction success vs STR shift magnitude")
        ax.legend()
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        plt.tight_layout()
        p = out_dir / "str_shift_magnitude.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        created.append(p)

    # ── Success rate vs bit-flip rate ───────────────────────────────────────
    bf_data = metrics.get("by_bit_flip", {})
    if bf_data:
        rates = sorted(bf_data.keys())
        successes = [bf_data[r]["success_rate"] for r in rates]

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([r * 100 for r in rates], successes, "o-", color="purple")
        ax.set_xlabel("Bit-flip rate (%)")
        ax.set_ylabel("Success rate")
        ax.set_title("Reconstruction success vs post-encoding bit-flip rate")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        p = out_dir / "bit_flip_rate.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        created.append(p)

    return created
