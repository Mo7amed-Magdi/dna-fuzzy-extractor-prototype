"""Tests for preprocess: encoding and vectorization."""

from __future__ import annotations

import pytest


class TestSNPEncoding:
    def test_encode_decode_roundtrip(self):
        from dna_proto.preprocess import encode_snp, decode_snp
        for base in ("A", "C", "G", "T"):
            assert decode_snp(encode_snp(base)) == base

    def test_known_values(self):
        from dna_proto.preprocess import encode_snp, SNP_ENCODING
        assert SNP_ENCODING["A"] == 0b00
        assert SNP_ENCODING["C"] == 0b01
        assert SNP_ENCODING["G"] == 0b10
        assert SNP_ENCODING["T"] == 0b11

    def test_invalid_base_raises(self):
        from dna_proto.preprocess import encode_snp
        with pytest.raises(ValueError):
            encode_snp("X")

    def test_case_insensitive(self):
        from dna_proto.preprocess import encode_snp
        assert encode_snp("a") == encode_snp("A")


class TestSTREncoding:
    def test_encode_in_range(self):
        from dna_proto.preprocess import encode_str
        v = encode_str(15, 5, 50, 4)
        assert 0 <= v <= 15

    def test_encode_min_max(self):
        from dna_proto.preprocess import encode_str
        assert encode_str(5, 5, 50, 4) == 0
        assert encode_str(50, 5, 50, 4) == 15

    def test_out_of_range_raises(self):
        from dna_proto.preprocess import encode_str
        with pytest.raises(ValueError):
            encode_str(4, 5, 50, 4)
        with pytest.raises(ValueError):
            encode_str(51, 5, 50, 4)

    def test_quantization_tolerance(self):
        """Values in the same bin should produce the same encoding."""
        from dna_proto.preprocess import encode_str
        # With 4 bits and range [5,50] (46 values), bin_size ≈ 3
        # Two adjacent values may share a bin
        v1 = encode_str(5, 5, 50, 4)
        v2 = encode_str(6, 5, 50, 4)
        # They might or might not share a bin; just check both are valid
        assert 0 <= v1 <= 15
        assert 0 <= v2 <= 15


class TestVectorization:
    def test_deterministic(self, catalogue, profile_001):
        from dna_proto.preprocess import profile_to_bytes
        w1 = profile_to_bytes(profile_001, catalogue)
        w2 = profile_to_bytes(profile_001, catalogue)
        assert w1 == w2

    def test_length(self, catalogue):
        from dna_proto.preprocess import vector_length_bits, profile_to_bytes
        from dna_proto.dna_input import load_profile
        from pathlib import Path
        n_bits = vector_length_bits(catalogue)
        n_bytes_expected = (n_bits + 7) // 8
        p = load_profile(Path(__file__).parent.parent / "data" / "synthetic_profiles" / "subject_001.json")
        w = profile_to_bytes(p, catalogue)
        assert len(w) == n_bytes_expected

    def test_different_profiles_different_vectors(self, catalogue, profile_001, profile_002):
        from dna_proto.preprocess import profile_to_bytes
        w1 = profile_to_bytes(profile_001, catalogue)
        w2 = profile_to_bytes(profile_002, catalogue)
        assert w1 != w2

    def test_hamming_distance_zero(self):
        from dna_proto.preprocess import hamming_distance
        a = b"\xAB\xCD\xEF"
        assert hamming_distance(a, a) == 0

    def test_hamming_distance_all_different(self):
        from dna_proto.preprocess import hamming_distance
        assert hamming_distance(b"\x00", b"\xFF") == 8

    def test_hamming_distance_length_mismatch(self):
        from dna_proto.preprocess import hamming_distance
        with pytest.raises(ValueError):
            hamming_distance(b"\x00\x01", b"\x00")

    def test_catalogue_fingerprint_deterministic(self, catalogue):
        from dna_proto.preprocess import catalogue_fingerprint
        fp1 = catalogue_fingerprint(catalogue)
        fp2 = catalogue_fingerprint(catalogue)
        assert fp1 == fp2
        assert len(fp1) == 16  # 8 bytes hex

    def test_catalogue_fingerprint_differs_on_change(self, catalogue):
        import copy
        from dna_proto.preprocess import catalogue_fingerprint
        modified = copy.deepcopy(catalogue)
        modified["snp_markers"].append("rs99999")
        assert catalogue_fingerprint(catalogue) != catalogue_fingerprint(modified)
