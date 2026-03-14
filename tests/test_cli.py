"""Tests for the CLI (`dna-proto` command)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

PROFILES_DIR = Path(__file__).parent.parent / "data" / "synthetic_profiles"


@pytest.fixture
def runner():
    return CliRunner()


class TestCLI:
    def test_gen_command(self, runner, tmp_path):
        from dna_proto.cli import main
        enr_path = tmp_path / "enrollment.json"
        result = runner.invoke(
            main,
            ["gen", "--in", str(PROFILES_DIR / "subject_001.json"), "--out", str(enr_path)],
        )
        assert result.exit_code == 0, result.output
        assert enr_path.exists()
        assert "Public key" in result.output

    def test_encrypt_decrypt_roundtrip(self, runner, tmp_path):
        from dna_proto.cli import main
        enr_path = tmp_path / "enr.json"
        in_file = tmp_path / "plain.txt"
        enc_file = tmp_path / "plain.txt.enc"
        dec_file = tmp_path / "plain_dec.txt"

        in_file.write_text("Top secret data!")

        # Enrol
        runner.invoke(
            main,
            ["gen", "--in", str(PROFILES_DIR / "subject_001.json"), "--out", str(enr_path)],
        )
        # Encrypt
        result = runner.invoke(
            main,
            [
                "encrypt",
                "--enrollment", str(enr_path),
                "--dna", str(PROFILES_DIR / "subject_001.json"),
                "--in", str(in_file),
                "--out", str(enc_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert enc_file.exists()
        # Decrypt
        result = runner.invoke(
            main,
            [
                "decrypt",
                "--enrollment", str(enr_path),
                "--dna", str(PROFILES_DIR / "subject_001.json"),
                "--in", str(enc_file),
                "--out", str(dec_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert dec_file.read_text() == "Top secret data!"

    def test_decrypt_wrong_dna_fails(self, runner, tmp_path):
        from dna_proto.cli import main
        enr_path = tmp_path / "enr.json"
        in_file = tmp_path / "plain.txt"
        enc_file = tmp_path / "plain.txt.enc"
        dec_file = tmp_path / "dec.txt"
        in_file.write_text("Secret!")

        runner.invoke(
            main,
            ["gen", "--in", str(PROFILES_DIR / "subject_001.json"), "--out", str(enr_path)],
        )
        runner.invoke(
            main,
            [
                "encrypt",
                "--enrollment", str(enr_path),
                "--dna", str(PROFILES_DIR / "subject_001.json"),
                "--in", str(in_file),
                "--out", str(enc_file),
            ],
        )
        # Attempt to decrypt with subject_002's DNA → should fail
        result = runner.invoke(
            main,
            [
                "decrypt",
                "--enrollment", str(enr_path),
                "--dna", str(PROFILES_DIR / "subject_002.json"),
                "--in", str(enc_file),
                "--out", str(dec_file),
            ],
        )
        assert result.exit_code != 0

    def test_fuzz_command(self, runner, tmp_path):
        from dna_proto.cli import main
        enr_path = tmp_path / "enr.json"
        out_path = tmp_path / "campaign.jsonl"
        runner.invoke(
            main,
            ["gen", "--in", str(PROFILES_DIR / "subject_001.json"), "--out", str(enr_path)],
        )
        result = runner.invoke(
            main,
            [
                "fuzz",
                "--enrollment", str(enr_path),
                "--seed-profile", str(PROFILES_DIR / "subject_001.json"),
                "--out", str(out_path),
                "--snp-rates", "0,0.05",
                "--str-shifts", "0,1",
                "--n", "3",
            ],
        )
        assert result.exit_code == 0, result.output
        assert out_path.exists()

    def test_report_command(self, runner, tmp_path):
        from dna_proto.cli import main
        enr_path = tmp_path / "enr.json"
        campaign_path = tmp_path / "campaign.jsonl"

        runner.invoke(
            main,
            ["gen", "--in", str(PROFILES_DIR / "subject_001.json"), "--out", str(enr_path)],
        )
        runner.invoke(
            main,
            [
                "fuzz",
                "--enrollment", str(enr_path),
                "--seed-profile", str(PROFILES_DIR / "subject_001.json"),
                "--out", str(campaign_path),
                "--snp-rates", "0,0.05",
                "--str-shifts", "0",
                "--n", "5",
            ],
        )
        result = runner.invoke(
            main,
            ["report", "--in", str(campaign_path), "--out", str(tmp_path / "report")],
        )
        assert result.exit_code == 0, result.output
        assert "success_rate" in result.output

    def test_experiment_command(self, runner, tmp_path):
        from dna_proto.cli import main
        result = runner.invoke(
            main,
            [
                "experiment",
                "--profile", str(PROFILES_DIR / "subject_001.json"),
                "--out", str(tmp_path),
                "--snp-rates", "0,0.05",
                "--str-shifts", "0",
                "--n", "3",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Experiment complete" in result.output
