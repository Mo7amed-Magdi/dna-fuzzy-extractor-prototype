"""Tests for DNA profile loading and schema validation."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from dna_proto.dna_input.loader import load_csv, load_json, load_profile
from dna_proto.dna_input.schema import (
    DNAProfile,
    STR_MAX,
    STR_MIN,
    profile_from_csv_text,
    validate_profile,
)


class TestSchema:
    def test_valid_profile(self):
        raw = {
            "subject_id": "S1",
            "snps": {"rs1": "A", "rs2": "G"},
            "strs": {"D3": 15, "vWA": 17},
        }
        profile = validate_profile(raw)
        assert isinstance(profile, DNAProfile)
        assert profile.subject_id == "S1"
        assert profile.snps["rs1"] == "A"
        assert profile.strs["D3"] == 15

    def test_lowercase_snp_is_normalized(self):
        raw = {"snps": {"rs1": "a"}, "strs": {}}
        profile = validate_profile(raw)
        assert profile.snps["rs1"] == "A"

    def test_invalid_snp_raises(self):
        raw = {"snps": {"rs1": "N"}, "strs": {}}
        with pytest.raises(ValueError, match="rs1"):
            validate_profile(raw)

    def test_str_out_of_range_raises(self):
        raw = {"snps": {}, "strs": {"D3": STR_MAX + 1}}
        with pytest.raises(ValueError, match="D3"):
            validate_profile(raw)

    def test_str_below_min_raises(self):
        raw = {"snps": {}, "strs": {"D3": STR_MIN - 1}}
        with pytest.raises(ValueError, match="D3"):
            validate_profile(raw)

    def test_str_non_integer_raises(self):
        raw = {"snps": {}, "strs": {"D3": "not_an_int"}}
        with pytest.raises(ValueError, match="D3"):
            validate_profile(raw)


class TestCSVParsing:
    def test_valid_csv(self):
        csv_text = (
            "subject_id,marker_type,marker_id,value\n"
            "S1,SNP,rs1,A\n"
            "S1,SNP,rs2,G\n"
            "S1,STR,D3,15\n"
        )
        profile = profile_from_csv_text(csv_text)
        assert profile.subject_id == "S1"
        assert profile.snps["rs1"] == "A"
        assert profile.strs["D3"] == 15

    def test_csv_multiple_subjects_raises(self):
        csv_text = (
            "subject_id,marker_type,marker_id,value\n"
            "S1,SNP,rs1,A\n"
            "S2,SNP,rs1,G\n"
        )
        with pytest.raises(ValueError, match="multiple subject IDs"):
            profile_from_csv_text(csv_text)

    def test_csv_invalid_marker_type_raises(self):
        csv_text = (
            "subject_id,marker_type,marker_id,value\n"
            "S1,INDEL,rs1,A\n"
        )
        with pytest.raises(ValueError, match="INDEL"):
            profile_from_csv_text(csv_text)


class TestLoaders:
    def test_load_json(self, tmp_path):
        profile_dict = {
            "subject_id": "T1",
            "snps": {"rs1": "C"},
            "strs": {"D3": 10},
        }
        p = tmp_path / "profile.json"
        p.write_text(json.dumps(profile_dict))
        profile = load_json(p)
        assert profile.subject_id == "T1"

    def test_load_csv(self, tmp_path):
        csv_text = "subject_id,marker_type,marker_id,value\nT2,SNP,rs1,T\nT2,STR,D3,20\n"
        p = tmp_path / "profile.csv"
        p.write_text(csv_text)
        profile = load_csv(p)
        assert profile.snps["rs1"] == "T"
        assert profile.strs["D3"] == 20

    def test_load_profile_auto_json(self, tmp_path):
        profile_dict = {"subject_id": "T3", "snps": {"rs1": "G"}, "strs": {"D3": 12}}
        p = tmp_path / "profile.json"
        p.write_text(json.dumps(profile_dict))
        profile = load_profile(p)
        assert profile.subject_id == "T3"

    def test_load_profile_unsupported_extension_raises(self, tmp_path):
        p = tmp_path / "profile.txt"
        p.write_text("hello")
        with pytest.raises(ValueError, match=".txt"):
            load_profile(p)
