"""Security evaluation metrics.

Computes per-noise-level statistics from campaign results:
- Reconstruction success rate
- FRR (False Rejection Rate): fraction of genuine attempts that fail
- FAR (False Acceptance Rate): fraction of impostor attempts that succeed
- Collision rate: fraction where an impostor produces a different success
  (Note: without key output logging, collision = FAR for this prototype)
- Hamming distance statistics
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def compute_metrics(results: list[dict]) -> dict[str, Any]:
    """Compute aggregate metrics from a list of campaign result dicts.

    Parameters
    ----------
    results:
        List of dicts as produced by :func:`~dna_proto.fuzzing.campaign.run_campaign`.

    Returns
    -------
    Dict with keys:
    - ``overall``: overall success rate, FRR, FAR.
    - ``by_snp_rate``: per-SNP-rate stats for genuine trials.
    - ``by_str_shift``: per-STR-shift stats for genuine trials.
    - ``by_bit_flip``: per-bit-flip-rate stats.
    - ``impostor``: FAR and collision rate.
    - ``hamming_stats``: mean/max Hamming distance by trial type.
    """
    genuine = [r for r in results if r["type"] == "genuine"]
    impostors = [r for r in results if r["type"] == "impostor"]
    bit_flips = [r for r in results if r["type"] == "bit_flip"]

    def _rate(items: list[dict], key: str = "success") -> float:
        if not items:
            return float("nan")
        return sum(1 for r in items if r[key]) / len(items)

    def _group_stats(items: list[dict], group_key: str) -> dict:
        grouped: dict = defaultdict(list)
        for r in items:
            grouped[r[group_key]].append(r)
        out = {}
        for gk, group in sorted(grouped.items()):
            successes = sum(1 for r in group if r["success"])
            hd_values = [r["hamming_distance"] for r in group]
            out[gk] = {
                "n_trials": len(group),
                "n_success": successes,
                "success_rate": successes / len(group),
                "frr": (len(group) - successes) / len(group),
                "mean_hamming": sum(hd_values) / len(hd_values) if hd_values else 0,
                "max_hamming": max(hd_values) if hd_values else 0,
            }
        return out

    n_genuine_fail = sum(1 for r in genuine if not r["success"])
    frr = n_genuine_fail / len(genuine) if genuine else float("nan")
    far = _rate(impostors)
    overall_success = _rate(genuine)

    return {
        "overall": {
            "n_genuine": len(genuine),
            "n_impostors": len(impostors),
            "n_bit_flip": len(bit_flips),
            "success_rate": overall_success,
            "frr": frr,
            "far": far,
            "collision_rate": far,  # FAR == collision rate without key logging
        },
        "by_snp_rate": _group_stats(genuine, "snp_rate"),
        "by_str_shift": _group_stats(genuine, "str_shift_mag"),
        "by_bit_flip": _group_stats(bit_flips, "flip_rate") if bit_flips else {},
        "impostor": {
            "n": len(impostors),
            "far": far,
        },
    }
