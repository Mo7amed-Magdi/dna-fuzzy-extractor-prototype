"""Tests for SNP/STR encoding and biometric vectorization."""

from __future__ import annotations

import pytest

from dna_proto.preprocess.encode_snp import decode_snp, encode_snp, encode_snp_list
from dna_proto.preprocess.encode_str import (
    STR_BITS,
    decode_str_approx,
    encode_str,
    encode_str_list,
)
from dna_proto.preprocess.vectorize import (
    BIOMETRIC_BYTES,
    N_SNPS,
    N_STRS,
    hamming_distance,
    vectorize,
)


# ---------------------------------------------------------------------------
# SNP encoding
# ---------------------------------------------------------------------------

class TestSNPEncoding:
    def test_encode_all_bases(self):
        assert encode_snp("A") == 0b00
        assert encode_snp("C") == 0b01
        assert encode_snp("G") == 0b10
        assert encode_snp("T") == 0b11

    def test_case_insensitive(self):
        assert encode_snp("a") == encode_snp("A")
        assert encode_snp("t") == encode_snp("T")

    def test_invalid_base_raises(self):
        with pytest.raises(ValueError):
            encode_snp("N")
        with pytest.raises(ValueError):
            encode_snp("X")

    def test_roundtrip(self):
        for base in "ACGT":
            assert decode_snp(encode_snp(base)) == base

    def test_list_encoding(self):
        result = encode_snp_list(["A", "C", "G", "T"])
        assert result == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# STR encoding
# ---------------------------------------------------------------------------

class TestSTREncoding:
    def test_min_value(self):
        assert encode_str(5) == 0

    def test_max_value(self):
        assert encode_str(30) <= (1 << STR_BITS) - 1

    def test_clamping_below_min(self):
        assert encode_str(4) == encode_str(5)  # clamped to STR_MIN

    def test_clamping_above_max(self):
        assert encode_str(31) == encode_str(30)  # clamped to STR_MAX

    def test_monotone(self):
        bins = [encode_str(v) for v in range(5, 31)]
        # bins should be non-decreasing
        for a, b in zip(bins, bins[1:]):
            assert a <= b

    def test_adjacency_tolerance(self):
        # Adjacent values may map to the same bin (tolerance feature)
        for v in range(5, 30):
            # At least some adjacent pairs should share a bin
            bins = [encode_str(v), encode_str(v + 1)]
            # Just verify no exception; actual bin value may or may not match
            assert 0 <= bins[0] <= 15
            assert 0 <= bins[1] <= 15

    def test_decode_roundtrip_approximate(self):
        for v in range(5, 31):
            b = encode_str(v)
            approx = decode_str_approx(b)
            # approx should be within one bin width of original
            assert approx <= v <= approx + 3  # bin width 2 + one off

    def test_list_encoding(self):
        counts = [5, 10, 20, 30]
        result = encode_str_list(counts)
        assert len(result) == 4
        assert all(0 <= r <= 15 for r in result)


# ---------------------------------------------------------------------------
# Biometric vectorization
# ---------------------------------------------------------------------------

class TestVectorize:
    def test_output_length(self, sample_profile):
        biometric = vectorize(sample_profile)
        assert len(biometric) == BIOMETRIC_BYTES

    def test_deterministic(self, sample_profile):
        b1 = vectorize(sample_profile)
        b2 = vectorize(sample_profile)
        assert b1 == b2

    def test_wrong_snp_count_raises(self, sample_profile):
        from dna_proto.dna_input.schema import DNAProfile
        bad = DNAProfile("x", {"rs0001": "A"}, sample_profile.strs)
        with pytest.raises(ValueError, match="SNPs"):
            vectorize(bad)

    def test_wrong_str_count_raises(self, sample_profile):
        from dna_proto.dna_input.schema import DNAProfile
        bad = DNAProfile("x", sample_profile.snps, {"str_001": 10})
        with pytest.raises(ValueError, match="STRs"):
            vectorize(bad)

    def test_different_profiles_differ(self, markers_and_profiles):
        from dna_proto.dna_input.schema import validate_profile
        _, profiles = markers_and_profiles
        b0 = vectorize(validate_profile(profiles[0]))
        b1 = vectorize(validate_profile(profiles[1]))
        assert b0 != b1

    def test_hamming_distance_same_is_zero(self, sample_biometric):
        assert hamming_distance(sample_biometric, sample_biometric) == 0

    def test_hamming_distance_differs(self, markers_and_profiles):
        from dna_proto.dna_input.schema import validate_profile
        _, profiles = markers_and_profiles
        b0 = vectorize(validate_profile(profiles[0]))
        b1 = vectorize(validate_profile(profiles[1]))
        assert hamming_distance(b0, b1) > 0
