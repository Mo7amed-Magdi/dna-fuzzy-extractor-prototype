"""Tests for adversarial fuzzing module."""

from __future__ import annotations

import random

import pytest


class TestMutators:
    def test_snp_substitution_rate_zero(self, profile_001):
        from dna_proto.fuzzing import snp_substitution
        mutated = snp_substitution(profile_001, rate=0.0)
        assert mutated["snps"] == profile_001["snps"]

    def test_snp_substitution_rate_one(self, catalogue, profile_001):
        from dna_proto.fuzzing import snp_substitution
        rng = random.Random(1)
        mutated = snp_substitution(profile_001, rate=1.0, rng=rng)
        changed = sum(
            1 for sid in catalogue["snp_markers"]
            if mutated["snps"][sid] != profile_001["snps"][sid]
        )
        assert changed > 0

    def test_snp_all_values_valid(self, catalogue, profile_001):
        from dna_proto.fuzzing import snp_substitution
        rng = random.Random(42)
        mutated = snp_substitution(profile_001, rate=0.5, rng=rng)
        for val in mutated["snps"].values():
            assert val in {"A", "C", "G", "T"}

    def test_str_shift_zero(self, catalogue, profile_001):
        from dna_proto.fuzzing import str_shift
        mutated = str_shift(profile_001, catalogue, 0)
        assert mutated["strs"] == profile_001["strs"]

    def test_str_shift_stays_in_bounds(self, catalogue, profile_001):
        from dna_proto.fuzzing import str_shift
        rng = random.Random(7)
        mutated = str_shift(profile_001, catalogue, 10, rng=rng)
        for entry in catalogue["str_markers"]:
            mid = entry["id"]
            assert entry["min"] <= mutated["strs"][mid] <= entry["max"]

    def test_boundary_test_min(self, catalogue, profile_001):
        from dna_proto.fuzzing import boundary_test
        mutated = boundary_test(profile_001, catalogue, push_to="min")
        for entry in catalogue["str_markers"]:
            assert mutated["strs"][entry["id"]] == entry["min"]

    def test_boundary_test_max(self, catalogue, profile_001):
        from dna_proto.fuzzing import boundary_test
        mutated = boundary_test(profile_001, catalogue, push_to="max")
        for entry in catalogue["str_markers"]:
            assert mutated["strs"][entry["id"]] == entry["max"]

    def test_bit_flip_vector_rate_zero(self, vector_001):
        from dna_proto.fuzzing import bit_flip_vector
        result = bit_flip_vector(vector_001, rate=0.0)
        assert result == vector_001

    def test_bit_flip_vector_rate_one(self, vector_001):
        from dna_proto.fuzzing import bit_flip_vector
        rng = random.Random(1)
        result = bit_flip_vector(vector_001, rate=1.0, rng=rng)
        assert result != vector_001

    def test_bit_flip_same_length(self, vector_001):
        from dna_proto.fuzzing import bit_flip_vector
        result = bit_flip_vector(vector_001, rate=0.1)
        assert len(result) == len(vector_001)

    def test_composite_mutate_no_mutation(self, catalogue, profile_001):
        from dna_proto.fuzzing import composite_mutate
        mutated = composite_mutate(
            profile_001, catalogue, snp_rate=0.0, str_shift_mag=0
        )
        assert mutated["snps"] == profile_001["snps"]
        assert mutated["strs"] == profile_001["strs"]

    def test_original_profile_not_modified(self, catalogue, profile_001):
        """Mutators must not modify the original profile (deep copy)."""
        import copy
        from dna_proto.fuzzing import snp_substitution
        orig_snps = copy.deepcopy(profile_001["snps"])
        snp_substitution(profile_001, rate=1.0)
        assert profile_001["snps"] == orig_snps


class TestCampaign:
    def test_run_campaign_zero_noise(self, profile_001, enrollment_001, catalogue):
        from dna_proto.fuzzing import run_campaign
        _, enrollment = enrollment_001
        results = run_campaign(
            profile_001,
            enrollment,
            catalogue,
            snp_rates=[0.0],
            str_shifts=[0],
            n_trials=5,
            seed=1,
        )
        assert all(r["success"] for r in results if r["type"] == "genuine")

    def test_run_campaign_high_snp_noise(self, profile_001, enrollment_001, catalogue):
        from dna_proto.fuzzing import run_campaign
        _, enrollment = enrollment_001
        results = run_campaign(
            profile_001,
            enrollment,
            catalogue,
            snp_rates=[0.5],
            str_shifts=[0],
            n_trials=20,
            seed=2,
        )
        genuine = [r for r in results if r["type"] == "genuine"]
        assert len(genuine) > 0
        # At high noise, most should fail
        n_fail = sum(1 for r in genuine if not r["success"])
        assert n_fail > 0

    def test_run_campaign_impostor(self, profile_001, profile_002, enrollment_001, catalogue):
        from dna_proto.fuzzing import run_campaign
        _, enrollment = enrollment_001
        results = run_campaign(
            profile_001,
            enrollment,
            catalogue,
            snp_rates=[0.0],
            str_shifts=[0],
            n_trials=2,
            impostor_profiles=[profile_002],
            seed=3,
        )
        impostor_results = [r for r in results if r["type"] == "impostor"]
        assert len(impostor_results) == 1
        assert not impostor_results[0]["success"]

    def test_run_campaign_writes_jsonl(self, profile_001, enrollment_001, catalogue, tmp_dir):
        import json
        from dna_proto.fuzzing import run_campaign
        _, enrollment = enrollment_001
        out_path = tmp_dir / "campaign.jsonl"
        run_campaign(
            profile_001,
            enrollment,
            catalogue,
            snp_rates=[0.0],
            str_shifts=[0],
            n_trials=3,
            out_path=out_path,
        )
        lines = [json.loads(l) for l in out_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3

    def test_load_results(self, profile_001, enrollment_001, catalogue, tmp_dir):
        from dna_proto.fuzzing import run_campaign, load_results
        _, enrollment = enrollment_001
        out_path = tmp_dir / "r.jsonl"
        run_campaign(
            profile_001, enrollment, catalogue,
            snp_rates=[0.0], str_shifts=[0], n_trials=2, out_path=out_path
        )
        loaded = load_results(out_path)
        assert len(loaded) == 2
