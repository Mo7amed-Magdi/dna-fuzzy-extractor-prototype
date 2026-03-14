"""Tests for evaluation metrics and report generation."""

from __future__ import annotations

import pytest


def _make_results(n_genuine_pass, n_genuine_fail, n_impostor_pass, n_impostor_fail):
    results = []
    for _ in range(n_genuine_pass):
        results.append({"type": "genuine", "snp_rate": 0.0, "str_shift_mag": 0,
                         "trial": 0, "hamming_distance": 0, "success": True, "ts": 0})
    for _ in range(n_genuine_fail):
        results.append({"type": "genuine", "snp_rate": 0.1, "str_shift_mag": 0,
                         "trial": 0, "hamming_distance": 10, "success": False, "ts": 0})
    for _ in range(n_impostor_pass):
        results.append({"type": "impostor", "subject_id": "S2",
                         "hamming_distance": 40, "success": True, "ts": 0})
    for _ in range(n_impostor_fail):
        results.append({"type": "impostor", "subject_id": "S2",
                         "hamming_distance": 40, "success": False, "ts": 0})
    return results


class TestMetrics:
    def test_frr_zero_for_all_success(self):
        from dna_proto.evaluation import compute_metrics
        results = _make_results(10, 0, 0, 5)
        m = compute_metrics(results)
        assert m["overall"]["frr"] == 0.0

    def test_frr_one_for_all_fail(self):
        from dna_proto.evaluation import compute_metrics
        results = _make_results(0, 10, 0, 5)
        m = compute_metrics(results)
        assert m["overall"]["frr"] == 1.0

    def test_far_zero_for_all_reject(self):
        from dna_proto.evaluation import compute_metrics
        results = _make_results(5, 0, 0, 10)
        m = compute_metrics(results)
        assert m["overall"]["far"] == 0.0

    def test_far_one_for_all_accept(self):
        from dna_proto.evaluation import compute_metrics
        results = _make_results(5, 0, 10, 0)
        m = compute_metrics(results)
        assert m["overall"]["far"] == 1.0

    def test_by_snp_rate_keys(self):
        from dna_proto.evaluation import compute_metrics
        results = _make_results(5, 5, 2, 2)
        m = compute_metrics(results)
        assert 0.0 in m["by_snp_rate"]
        assert 0.1 in m["by_snp_rate"]

    def test_empty_results(self):
        from dna_proto.evaluation import compute_metrics
        import math
        m = compute_metrics([])
        assert math.isnan(m["overall"]["frr"])

    def test_n_genuine_n_impostors(self):
        from dna_proto.evaluation import compute_metrics
        results = _make_results(7, 3, 4, 1)
        m = compute_metrics(results)
        assert m["overall"]["n_genuine"] == 10
        assert m["overall"]["n_impostors"] == 5


class TestReport:
    def test_save_summary(self, tmp_dir):
        import json
        from dna_proto.evaluation import save_summary, compute_metrics
        results = _make_results(5, 0, 0, 3)
        m = compute_metrics(results)
        path = tmp_dir / "summary.json"
        save_summary(m, path)
        loaded = json.loads(path.read_text())
        assert "overall" in loaded

    def test_generate_plots(self, tmp_dir):
        from dna_proto.evaluation import compute_metrics, generate_plots
        results = _make_results(5, 5, 0, 2)
        m = compute_metrics(results)
        plots = generate_plots(m, tmp_dir / "plots")
        # Plots should be generated (matplotlib available)
        assert isinstance(plots, list)
