"""Tests for evaluation metrics and report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dna_proto.evaluation.metrics import compute_metrics
from dna_proto.evaluation.report import generate_report, load_jsonl, save_jsonl


def _make_results(n_genuine_ok, n_genuine_fail, n_impostor_ok, n_impostor_fail):
    results = []
    pub = "aa" * 32
    for _ in range(n_genuine_ok):
        results.append({
            "attempt_type": "genuine",
            "n_snp_mutations": 0,
            "success": True,
            "public_key_hex": pub,
        })
    for _ in range(n_genuine_fail):
        results.append({
            "attempt_type": "genuine",
            "n_snp_mutations": 8,
            "success": False,
            "public_key_hex": None,
        })
    for _ in range(n_impostor_ok):
        results.append({
            "attempt_type": "impostor",
            "impostor_id": "S2",
            "success": True,
            "public_key_hex": "bb" * 32,  # different key → no collision
        })
    for _ in range(n_impostor_fail):
        results.append({
            "attempt_type": "impostor",
            "impostor_id": "S3",
            "success": False,
            "public_key_hex": None,
        })
    return results


class TestMetrics:
    def test_perfect_genuine_zero_impostor(self):
        results = _make_results(100, 0, 0, 10)
        m = compute_metrics(results)
        assert m["success_rate"] == 1.0
        assert m["frr"] == 0.0
        assert m["far"] == 0.0
        assert m["n_genuine"] == 100

    def test_frr_computation(self):
        results = _make_results(80, 20, 0, 100)
        m = compute_metrics(results)
        assert abs(m["frr"] - 0.2) < 1e-9
        assert abs(m["success_rate"] - 0.8) < 1e-9

    def test_far_computation(self):
        results = _make_results(100, 0, 5, 95)
        m = compute_metrics(results)
        assert abs(m["far"] - 0.05) < 1e-9

    def test_empty_results(self):
        m = compute_metrics([])
        assert m["n_genuine"] == 0
        assert m["n_impostor"] == 0
        assert m["success_rate"] == 0.0

    def test_per_level_breakdown(self):
        results = [
            {"attempt_type": "genuine", "n_snp_mutations": 0, "success": True, "public_key_hex": None},
            {"attempt_type": "genuine", "n_snp_mutations": 0, "success": True, "public_key_hex": None},
            {"attempt_type": "genuine", "n_snp_mutations": 4, "success": False, "public_key_hex": None},
        ]
        m = compute_metrics(results)
        assert m["per_level"][0]["success_rate"] == 1.0
        assert m["per_level"][4]["success_rate"] == 0.0

    def test_key_collision_rate(self):
        # One genuine success with pub key 'aa..', one impostor with same key
        pub = "aa" * 32
        results = [
            {"attempt_type": "genuine", "n_snp_mutations": 0, "success": True, "public_key_hex": pub},
            {"attempt_type": "impostor", "impostor_id": "X", "success": True, "public_key_hex": pub},
        ]
        m = compute_metrics(results)
        assert m["key_collision_rate"] == 1.0


class TestReport:
    def test_generate_report_creates_files(self, tmp_path):
        results = _make_results(50, 10, 0, 20)
        metrics = generate_report(results, tmp_path)
        assert (tmp_path / "summary.json").exists()
        assert (tmp_path / "far_frr.png").exists()

    def test_generate_report_returns_metrics(self, tmp_path):
        results = _make_results(100, 0, 0, 0)
        metrics = generate_report(results, tmp_path)
        assert "success_rate" in metrics

    def test_save_load_jsonl(self, tmp_path):
        data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        path = tmp_path / "test.jsonl"
        save_jsonl(data, path)
        loaded = load_jsonl(path)
        assert loaded == data

    def test_success_rate_plot_created_when_multilevel(self, tmp_path):
        results = []
        for lvl in [0, 2, 4]:
            for i in range(5):
                results.append({
                    "attempt_type": "genuine",
                    "n_snp_mutations": lvl,
                    "success": lvl == 0,
                    "public_key_hex": None,
                })
        generate_report(results, tmp_path)
        assert (tmp_path / "success_rate_vs_mutations.png").exists()
