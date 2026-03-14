"""Tests for adversarial fuzzing mutators and campaign."""

from __future__ import annotations

import copy
import random

import pytest

from dna_proto.fuzzing.mutators import (
    mutate_bit_flip,
    mutate_boundary_str,
    mutate_realistic,
    mutate_snp_substitution,
    mutate_str_shift,
)


@pytest.fixture
def small_profile():
    """Minimal profile dict for testing mutators (not a valid biometric profile)."""
    return {
        "subject_id": "T1",
        "snps": {"rs1": "A", "rs2": "C", "rs3": "G", "rs4": "T"},
        "strs": {"D3": 15, "vWA": 12},
    }


class TestMutateSNP:
    def test_exact_n_mutations(self, small_profile):
        rng = random.Random(0)
        mutated = mutate_snp_substitution(small_profile, n_mutations=2, rng=rng)
        changed = sum(
            1 for k in small_profile["snps"]
            if small_profile["snps"][k] != mutated["snps"][k]
        )
        assert changed == 2

    def test_zero_mutations_unchanged(self, small_profile):
        rng = random.Random(0)
        mutated = mutate_snp_substitution(small_profile, n_mutations=0, rng=rng)
        assert mutated["snps"] == small_profile["snps"]

    def test_mutation_changes_base(self, small_profile):
        rng = random.Random(0)
        for _ in range(10):
            mutated = mutate_snp_substitution(small_profile, n_mutations=1, rng=rng)
            for k in small_profile["snps"]:
                if small_profile["snps"][k] != mutated["snps"][k]:
                    assert mutated["snps"][k] in "ACGT"
                    assert mutated["snps"][k] != small_profile["snps"][k]

    def test_original_not_modified(self, small_profile):
        orig = copy.deepcopy(small_profile)
        rng = random.Random(0)
        mutate_snp_substitution(small_profile, n_mutations=2, rng=rng)
        assert small_profile["snps"] == orig["snps"]

    def test_clamp_to_available_snps(self, small_profile):
        rng = random.Random(0)
        mutated = mutate_snp_substitution(small_profile, n_mutations=100, rng=rng)
        # All SNPs changed (capped to available count)
        assert mutated is not small_profile


class TestMutateSTR:
    def test_exact_n_mutations(self, small_profile):
        rng = random.Random(1)
        mutated = mutate_str_shift(small_profile, n_mutations=1, rng=rng)
        changed = sum(
            1 for k in small_profile["strs"]
            if small_profile["strs"][k] != mutated["strs"][k]
        )
        assert changed == 1

    def test_values_stay_in_range(self, small_profile):
        rng = random.Random(2)
        for _ in range(20):
            mutated = mutate_str_shift(small_profile, n_mutations=2, rng=rng)
            for val in mutated["strs"].values():
                assert 5 <= val <= 30

    def test_boundary_mutation(self, small_profile):
        rng = random.Random(3)
        mutated = mutate_boundary_str(small_profile, rng=rng)
        boundary_vals = {5, 30}
        changed_to_boundary = any(
            v in boundary_vals for v in mutated["strs"].values()
        )
        assert changed_to_boundary


class TestMutateBitFlip:
    def test_exact_n_flips(self):
        import os
        bio = os.urandom(96)
        rng = random.Random(0)
        noisy = mutate_bit_flip(bio, n_flips=10, rng=rng)
        from dna_proto.preprocess.vectorize import hamming_distance
        assert hamming_distance(bio, noisy) == 10

    def test_zero_flips_unchanged(self):
        import os
        bio = os.urandom(96)
        rng = random.Random(0)
        noisy = mutate_bit_flip(bio, n_flips=0, rng=rng)
        assert noisy == bio

    def test_original_unchanged(self):
        import os
        bio = os.urandom(96)
        orig = bio
        rng = random.Random(0)
        mutate_bit_flip(bio, n_flips=5, rng=rng)
        assert bio == orig  # bytes are immutable


class TestRealisticMutation:
    def test_returns_valid_profile(self, small_profile):
        rng = random.Random(0)
        mutated = mutate_realistic(small_profile, snp_rate=1.0, str_rate=1.0, rng=rng)
        for base in mutated["snps"].values():
            assert base in "ACGT"
        for val in mutated["strs"].values():
            assert 5 <= val <= 30

    def test_no_mutation_at_zero_rate(self, small_profile):
        rng = random.Random(0)
        mutated = mutate_realistic(small_profile, snp_rate=0.0, str_rate=0.0, rng=rng)
        assert mutated["snps"] == small_profile["snps"]
        assert mutated["strs"] == small_profile["strs"]


class TestCampaign:
    def test_campaign_returns_results(self, sample_profile_dict, enrollment):
        from dna_proto.fuzzing.campaign import run_campaign
        results = run_campaign(
            seed_profile_dict=sample_profile_dict,
            helper_data=enrollment,
            impostor_dicts=[],
            mutation_levels=[0],
            n_trials_per_level=5,
            seed=0,
        )
        assert len(results) == 5
        for r in results:
            assert r["attempt_type"] == "genuine"
            assert "success" in r

    def test_zero_mutation_all_succeed(self, sample_profile_dict, enrollment):
        from dna_proto.fuzzing.campaign import run_campaign
        results = run_campaign(
            seed_profile_dict=sample_profile_dict,
            helper_data=enrollment,
            impostor_dicts=[],
            mutation_levels=[0],
            n_trials_per_level=10,
            seed=0,
        )
        assert all(r["success"] for r in results)

    def test_impostor_trials_included(
        self, sample_profile_dict, enrollment, markers_and_profiles
    ):
        from dna_proto.fuzzing.campaign import run_campaign
        _, profiles = markers_and_profiles
        impostor_dicts = profiles[1:]
        results = run_campaign(
            seed_profile_dict=sample_profile_dict,
            helper_data=enrollment,
            impostor_dicts=impostor_dicts,
            mutation_levels=[0],
            n_trials_per_level=2,
            seed=0,
        )
        impostor_results = [r for r in results if r["attempt_type"] == "impostor"]
        assert len(impostor_results) == len(impostor_dicts)
