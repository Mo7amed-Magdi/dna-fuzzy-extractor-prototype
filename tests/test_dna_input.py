"""Tests for dna_input: loader and schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest

PROFILES_DIR = Path(__file__).parent.parent / "data" / "synthetic_profiles"


class TestLoader:
    def test_load_json(self):
        from dna_proto.dna_input import load_profile
        p = load_profile(PROFILES_DIR / "subject_001.json")
        assert p["subject_id"] == "subject_001"
        assert isinstance(p["snps"], dict)
        assert isinstance(p["strs"], dict)
        assert len(p["snps"]) == 256
        assert len(p["strs"]) == 32

    def test_load_csv(self):
        from dna_proto.dna_input import load_profile
        p = load_profile(PROFILES_DIR / "subject_001.csv")
        assert isinstance(p["snps"], dict)
        assert isinstance(p["strs"], dict)
        assert len(p["snps"]) == 256

    def test_snp_values_uppercase(self):
        from dna_proto.dna_input import load_profile
        p = load_profile(PROFILES_DIR / "subject_001.json")
        for val in p["snps"].values():
            assert val in {"A", "C", "G", "T"}, f"Unexpected SNP value: {val}"

    def test_str_values_int(self):
        from dna_proto.dna_input import load_profile
        p = load_profile(PROFILES_DIR / "subject_001.json")
        for val in p["strs"].values():
            assert isinstance(val, int), f"STR value is not int: {val}"

    def test_unsupported_format_raises(self, tmp_path):
        from dna_proto.dna_input import load_profile
        bad = tmp_path / "x.txt"
        bad.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_profile(bad)


class TestSchema:
    def test_load_catalogue(self):
        from dna_proto.dna_input import load_marker_catalogue
        cat = load_marker_catalogue()
        assert "snp_markers" in cat
        assert "str_markers" in cat
        assert len(cat["snp_markers"]) == 256
        assert len(cat["str_markers"]) == 32

    def test_validate_profile_pass(self, catalogue, profile_001):
        from dna_proto.dna_input import validate_profile
        validate_profile(profile_001, catalogue)  # should not raise

    def test_validate_profile_missing_snp(self, catalogue, profile_001):
        import copy
        from dna_proto.dna_input import validate_profile
        bad = copy.deepcopy(profile_001)
        del bad["snps"][catalogue["snp_markers"][0]]
        with pytest.raises(ValueError, match="Missing SNP marker"):
            validate_profile(bad, catalogue)

    def test_validate_profile_invalid_base(self, catalogue, profile_001):
        import copy
        from dna_proto.dna_input import validate_profile
        bad = copy.deepcopy(profile_001)
        bad["snps"][catalogue["snp_markers"][0]] = "X"
        with pytest.raises(ValueError, match="invalid value"):
            validate_profile(bad, catalogue)

    def test_validate_profile_str_out_of_range(self, catalogue, profile_001):
        import copy
        from dna_proto.dna_input import validate_profile
        bad = copy.deepcopy(profile_001)
        str_id = catalogue["str_markers"][0]["id"]
        bad["strs"][str_id] = 999
        with pytest.raises(ValueError, match="out of range"):
            validate_profile(bad, catalogue)

    def test_validate_catalogue_missing_key(self):
        from dna_proto.dna_input.schema import _validate_catalogue
        with pytest.raises(ValueError, match="snp_markers"):
            _validate_catalogue({"str_markers": []})

    def test_validate_catalogue_invalid_str_entry(self):
        from dna_proto.dna_input.schema import _validate_catalogue
        with pytest.raises(ValueError):
            _validate_catalogue({
                "snp_markers": ["rs1"],
                "str_markers": [{"id": "bad", "min": 10, "max": 5, "n_bits": 4}],
            })
