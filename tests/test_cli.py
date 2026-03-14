"""Tests for the CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dna_proto.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def profile_json_path(tmp_path, sample_profile_dict):
    p = tmp_path / "subject.json"
    p.write_text(json.dumps(sample_profile_dict))
    return p


@pytest.fixture
def enrollment_path(tmp_path, sample_biometric):
    from dna_proto.fuzzy_extractor.gen import gen
    _secret, helper = gen(sample_biometric)
    p = tmp_path / "enrollment.json"
    p.write_text(json.dumps(helper))
    return p


class TestCLIGen:
    def test_gen_creates_enrollment(self, runner, tmp_path, profile_json_path):
        out = tmp_path / "enrollment.json"
        result = runner.invoke(main, ["gen", "--in", str(profile_json_path), "--out", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text())
        assert "sketch" in data
        assert "public_key" in data

    def test_gen_missing_input_fails(self, runner, tmp_path):
        out = tmp_path / "enrollment.json"
        result = runner.invoke(main, ["gen", "--in", "/nonexistent.json", "--out", str(out)])
        assert result.exit_code != 0


class TestCLIEncryptDecrypt:
    def test_encrypt_decrypt_roundtrip(
        self, runner, tmp_path, profile_json_path, enrollment_path
    ):
        plaintext = b"secret medical data"
        pt_path = tmp_path / "plain.txt"
        pt_path.write_bytes(plaintext)
        enc_path = tmp_path / "cipher.enc"
        dec_path = tmp_path / "recovered.txt"

        # encrypt
        result = runner.invoke(main, [
            "encrypt",
            "--enrollment", str(enrollment_path),
            "--dna", str(profile_json_path),
            "--in", str(pt_path),
            "--out", str(enc_path),
        ])
        assert result.exit_code == 0, result.output
        assert enc_path.exists()

        # decrypt
        result = runner.invoke(main, [
            "decrypt",
            "--enrollment", str(enrollment_path),
            "--dna", str(profile_json_path),
            "--in", str(enc_path),
            "--out", str(dec_path),
        ])
        assert result.exit_code == 0, result.output
        assert dec_path.read_bytes() == plaintext

    def test_decrypt_wrong_dna_fails(
        self, runner, tmp_path, profile_json_path, enrollment_path, markers_and_profiles
    ):
        _, profiles = markers_and_profiles
        impostor_dict = profiles[2]  # different subject
        impostor_path = tmp_path / "impostor.json"
        impostor_path.write_text(json.dumps(impostor_dict))

        plaintext = b"secret"
        pt_path = tmp_path / "plain.txt"
        pt_path.write_bytes(plaintext)
        enc_path = tmp_path / "cipher.enc"
        dec_path = tmp_path / "recovered.txt"

        runner.invoke(main, [
            "encrypt",
            "--enrollment", str(enrollment_path),
            "--dna", str(profile_json_path),
            "--in", str(pt_path),
            "--out", str(enc_path),
        ])

        result = runner.invoke(main, [
            "decrypt",
            "--enrollment", str(enrollment_path),
            "--dna", str(impostor_path),
            "--in", str(enc_path),
            "--out", str(dec_path),
        ])
        assert result.exit_code != 0  # reconstruction should fail


class TestCLIFuzzCampaign:
    def test_fuzz_campaign_runs(
        self, runner, tmp_path, profile_json_path, enrollment_path
    ):
        out = tmp_path / "campaign.jsonl"
        result = runner.invoke(main, [
            "fuzz-campaign",
            "--enrollment", str(enrollment_path),
            "--seed", str(profile_json_path),
            "--levels", "0,1",
            "--n", "3",
            "--out", str(out),
        ])
        assert result.exit_code == 0, result.output
        assert out.exists()
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        assert len(lines) == 6  # 2 levels × 3 trials


class TestCLIReport:
    def test_report_generates_files(self, runner, tmp_path):
        from dna_proto.evaluation.report import save_jsonl
        results = [
            {"attempt_type": "genuine", "n_snp_mutations": 0, "success": True, "public_key_hex": None},
            {"attempt_type": "genuine", "n_snp_mutations": 2, "success": False, "public_key_hex": None},
        ]
        jsonl_path = tmp_path / "results.jsonl"
        save_jsonl(results, jsonl_path)
        out_dir = tmp_path / "report"

        result = runner.invoke(main, [
            "report",
            "--in", str(jsonl_path),
            "--out", str(out_dir),
        ])
        assert result.exit_code == 0, result.output
        assert (out_dir / "summary.json").exists()
