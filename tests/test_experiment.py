"""Tests for the experiment controller."""

from __future__ import annotations

from pathlib import Path

import pytest

PROFILES_DIR = Path(__file__).parent.parent / "data" / "synthetic_profiles"


class TestExperiment:
    def test_run_experiment_creates_artifacts(self, tmp_dir):
        from dna_proto.controller import run_experiment
        metrics = run_experiment(
            PROFILES_DIR / "subject_001.json",
            out_dir=tmp_dir,
            snp_rates=[0.0, 0.05],
            str_shifts=[0, 1],
            n_trials=5,
            seed=99,
        )
        # Enrollment artifact created
        enr_files = list(tmp_dir.glob("enrollment_*.json"))
        assert len(enr_files) == 1

        # JSONL campaign log created
        campaign_files = list(tmp_dir.glob("campaign_*.jsonl"))
        assert len(campaign_files) == 1
        lines = campaign_files[0].read_text().splitlines()
        assert len(lines) > 0

        # Summary JSON created
        summary_files = list(tmp_dir.glob("summary_*.json"))
        assert len(summary_files) == 1

    def test_run_experiment_metrics_structure(self, tmp_dir):
        from dna_proto.controller import run_experiment
        metrics = run_experiment(
            PROFILES_DIR / "subject_001.json",
            out_dir=tmp_dir,
            snp_rates=[0.0],
            str_shifts=[0],
            n_trials=3,
            seed=1,
        )
        assert "overall" in metrics
        assert "frr" in metrics["overall"]
        assert "far" in metrics["overall"]

    def test_run_experiment_zero_noise_perfect_success(self, tmp_dir):
        from dna_proto.controller import run_experiment
        metrics = run_experiment(
            PROFILES_DIR / "subject_001.json",
            out_dir=tmp_dir,
            snp_rates=[0.0],
            str_shifts=[0],
            n_trials=10,
            seed=2,
        )
        assert metrics["overall"]["frr"] == 0.0
        assert metrics["overall"]["success_rate"] == 1.0

    def test_run_experiment_with_impostors(self, tmp_dir):
        from dna_proto.controller import run_experiment
        metrics = run_experiment(
            PROFILES_DIR / "subject_001.json",
            impostor_profile_paths=[
                PROFILES_DIR / "subject_002.json",
                PROFILES_DIR / "subject_003.json",
            ],
            out_dir=tmp_dir,
            snp_rates=[0.0],
            str_shifts=[0],
            n_trials=3,
            seed=3,
        )
        assert metrics["overall"]["n_impostors"] == 2
        assert metrics["overall"]["far"] == 0.0  # all impostors should fail
