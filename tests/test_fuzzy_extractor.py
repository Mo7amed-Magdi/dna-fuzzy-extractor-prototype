"""Tests for the fuzzy extractor (Gen / Rep)."""

from __future__ import annotations

import os

import pytest


class TestGen:
    def test_gen_returns_key_and_enrollment(self, vector_001, catalogue):
        from dna_proto.fuzzy_extractor import gen
        from dna_proto.preprocess import catalogue_fingerprint
        cat_fp = catalogue_fingerprint(catalogue)
        key, enr = gen(vector_001, cat_fp)
        assert isinstance(key, bytes)
        assert len(key) == 32
        assert "helper_data" in enr
        assert "verifier_tag" in enr
        assert "salt" in enr
        assert "n_bytes" in enr

    def test_enrollment_does_not_contain_raw_dna(self, vector_001, catalogue):
        """Helper data should not equal the original vector (it's XOR'd)."""
        from dna_proto.fuzzy_extractor import gen
        from dna_proto.preprocess import catalogue_fingerprint
        cat_fp = catalogue_fingerprint(catalogue)
        _, enr = gen(vector_001, cat_fp)
        helper = bytes.fromhex(enr["helper_data"])
        assert helper != vector_001

    def test_gen_nondeterministic(self, vector_001, catalogue):
        """Two Gen calls should produce different salts and helper data."""
        from dna_proto.fuzzy_extractor import gen
        from dna_proto.preprocess import catalogue_fingerprint
        cat_fp = catalogue_fingerprint(catalogue)
        _, enr1 = gen(vector_001, cat_fp)
        _, enr2 = gen(vector_001, cat_fp)
        assert enr1["salt"] != enr2["salt"]

    def test_save_load_enrollment(self, vector_001, catalogue, tmp_dir):
        from dna_proto.fuzzy_extractor import gen, save_enrollment, load_enrollment
        from dna_proto.preprocess import catalogue_fingerprint
        cat_fp = catalogue_fingerprint(catalogue)
        _, enr = gen(vector_001, cat_fp)
        path = tmp_dir / "enrollment.json"
        save_enrollment(enr, path)
        loaded = load_enrollment(path)
        assert loaded["helper_data"] == enr["helper_data"]
        assert loaded["verifier_tag"] == enr["verifier_tag"]


class TestRep:
    def test_rep_succeeds_exact_match(self, vector_001, enrollment_001):
        from dna_proto.fuzzy_extractor import rep
        key_material, enrollment = enrollment_001
        recovered = rep(vector_001, enrollment)
        assert recovered == key_material

    def test_rep_fails_wrong_vector(self, vector_001, enrollment_001):
        from dna_proto.fuzzy_extractor import rep, ReconstructionError
        key_material, enrollment = enrollment_001
        wrong = bytes(b ^ 0xFF for b in vector_001)  # flip all bits
        with pytest.raises(ReconstructionError):
            rep(wrong, enrollment)

    def test_rep_fails_length_mismatch(self, enrollment_001):
        from dna_proto.fuzzy_extractor import rep
        _, enrollment = enrollment_001
        with pytest.raises(ValueError, match="length mismatch"):
            rep(b"\x00" * 10, enrollment)

    def test_rep_same_key_on_repeated_calls(self, vector_001, enrollment_001):
        from dna_proto.fuzzy_extractor import rep
        _, enrollment = enrollment_001
        k1 = rep(vector_001, enrollment)
        k2 = rep(vector_001, enrollment)
        assert k1 == k2

    def test_rep_single_bit_flip_fails(self, vector_001, enrollment_001):
        """Without ECC, even a single bit flip should cause rejection."""
        from dna_proto.fuzzy_extractor import rep, ReconstructionError
        _, enrollment = enrollment_001
        arr = bytearray(vector_001)
        arr[0] ^= 0x01  # flip LSB of first byte
        with pytest.raises(ReconstructionError):
            rep(bytes(arr), enrollment)

    def test_rep_impostor_fails(self, catalogue, profile_002, enrollment_001):
        from dna_proto.fuzzy_extractor import rep, ReconstructionError
        from dna_proto.preprocess import profile_to_bytes
        _, enrollment = enrollment_001
        w2 = profile_to_bytes(profile_002, catalogue)
        with pytest.raises(ReconstructionError):
            rep(w2, enrollment)
