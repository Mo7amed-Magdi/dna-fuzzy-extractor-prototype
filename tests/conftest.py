"""Shared pytest fixtures for the dna-proto test suite."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
PROFILES_DIR = DATA_DIR / "synthetic_profiles"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def catalogue():
    from dna_proto.dna_input import load_marker_catalogue
    return load_marker_catalogue()


@pytest.fixture(scope="session")
def profile_001():
    from dna_proto.dna_input import load_profile
    return load_profile(PROFILES_DIR / "subject_001.json")


@pytest.fixture(scope="session")
def profile_002():
    from dna_proto.dna_input import load_profile
    return load_profile(PROFILES_DIR / "subject_002.json")


@pytest.fixture(scope="session")
def all_profiles():
    from dna_proto.dna_input import load_profile
    return [load_profile(p) for p in sorted(PROFILES_DIR.glob("subject_*.json"))]


@pytest.fixture(scope="session")
def vector_001(catalogue, profile_001):
    from dna_proto.preprocess import profile_to_bytes
    return profile_to_bytes(profile_001, catalogue)


@pytest.fixture(scope="session")
def enrollment_001(vector_001, catalogue):
    from dna_proto.fuzzy_extractor import gen
    from dna_proto.preprocess import catalogue_fingerprint
    cat_fp = catalogue_fingerprint(catalogue)
    key_material, enrollment = gen(vector_001, cat_fp)
    return key_material, enrollment


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path
