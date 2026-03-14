"""Shared pytest fixtures."""

from __future__ import annotations

import random

import pytest

from dna_proto.data_gen.generate_synthetic import generate_profiles
from dna_proto.dna_input.schema import validate_profile
from dna_proto.preprocess.vectorize import N_SNPS, N_STRS


@pytest.fixture(scope="session")
def markers_and_profiles():
    """Generate a set of synthetic profiles for testing."""
    markers, profiles = generate_profiles(n_subjects=5, seed=9999)
    return markers, profiles


@pytest.fixture(scope="session")
def sample_profile_dict(markers_and_profiles):
    _, profiles = markers_and_profiles
    return profiles[0]


@pytest.fixture(scope="session")
def sample_profile(sample_profile_dict):
    return validate_profile(sample_profile_dict)


@pytest.fixture(scope="session")
def sample_biometric(sample_profile):
    from dna_proto.preprocess.vectorize import vectorize
    return vectorize(sample_profile)


@pytest.fixture(scope="session")
def enrollment(sample_biometric):
    from dna_proto.fuzzy_extractor.gen import gen
    _secret, helper_data = gen(sample_biometric)
    return helper_data
