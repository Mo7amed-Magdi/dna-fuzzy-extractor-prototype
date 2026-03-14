"""Evaluation metrics computation."""

from __future__ import annotations

from collections import defaultdict


def compute_metrics(results: list[dict]) -> dict:
    """Compute FAR, FRR, success rate, and key collision from campaign results.

    Args:
        results: List of trial dicts produced by the campaign runner.
                 Each dict has at minimum: attempt_type ('genuine'/'impostor'),
                 success (bool), public_key_hex (str or None).

    Returns:
        Metrics dict with keys:
            n_genuine, n_impostor,
            genuine_success, impostor_success,
            success_rate, frr, far,
            key_collision_rate,
            per_level (dict of level → {n, successes, success_rate})
    """
    genuine = [r for r in results if r["attempt_type"] == "genuine"]
    impostor = [r for r in results if r["attempt_type"] == "impostor"]

    n_genuine = len(genuine)
    n_impostor = len(impostor)

    genuine_successes = sum(1 for r in genuine if r["success"])
    impostor_successes = sum(1 for r in impostor if r["success"])

    success_rate = genuine_successes / n_genuine if n_genuine else 0.0
    frr = 1.0 - success_rate
    far = impostor_successes / n_impostor if n_impostor else 0.0

    # Key collision: fraction of impostor successes that also produce the
    # *same* public key as a genuine success (very rare by design)
    genuine_pub_keys: set[str] = {
        r["public_key_hex"] for r in genuine if r.get("public_key_hex")
    }
    collisions = sum(
        1 for r in impostor
        if r["success"] and r.get("public_key_hex") in genuine_pub_keys
    )
    key_collision_rate = collisions / n_impostor if n_impostor else 0.0

    # Per-level breakdown for genuine trials
    per_level: dict[int, dict] = defaultdict(lambda: {"n": 0, "successes": 0})
    for r in genuine:
        lvl = r.get("n_snp_mutations", 0)
        per_level[lvl]["n"] += 1
        if r["success"]:
            per_level[lvl]["successes"] += 1
    per_level_final = {}
    for lvl, data in sorted(per_level.items()):
        n = data["n"]
        s = data["successes"]
        per_level_final[lvl] = {
            "n": n,
            "successes": s,
            "success_rate": s / n if n else 0.0,
        }

    return {
        "n_genuine": n_genuine,
        "n_impostor": n_impostor,
        "genuine_success": genuine_successes,
        "impostor_success": impostor_successes,
        "success_rate": success_rate,
        "frr": frr,
        "far": far,
        "key_collision_rate": key_collision_rate,
        "per_level": per_level_final,
    }
