"""CLI entry-point for dna-proto.

Commands:
  gen          Enrol a DNA profile and output enrollment artifacts.
  encrypt      Encrypt a file using a DNA-derived key.
  decrypt      Decrypt a file using a DNA-derived key.
  fuzz         Run an adversarial fuzz campaign.
  report       Generate summary and plots from a JSONL campaign log.
  experiment   Run the complete pipeline end-to-end.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .controller.experiment import run_experiment
from .crypto.hybrid_encrypt import decrypt, encrypt
from .dna_input.loader import load_profile
from .dna_input.schema import load_marker_catalogue, validate_profile
from .evaluation.metrics import compute_metrics
from .evaluation.report import generate_plots, save_summary
from .fuzzy_extractor.gen import gen, load_enrollment, save_enrollment
from .fuzzy_extractor.rep import ReconstructionError, rep
from .fuzzing.campaign import load_results, run_campaign
from .kdf_keys.x25519_keys import derive_x25519_keypair, public_key_bytes
from .preprocess.vectorize import catalogue_fingerprint, profile_to_bytes


@click.group()
@click.version_option()
def main() -> None:
    """DNA Fuzzy Extractor Research Prototype CLI."""


# ── gen ───────────────────────────────────────────────────────────────────────


@main.command()
@click.option(
    "--in",
    "profile_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to subject DNA profile (JSON or CSV).",
)
@click.option(
    "--out",
    "out_path",
    required=True,
    type=click.Path(),
    help="Output path for enrollment artifact JSON.",
)
@click.option(
    "--catalogue",
    "catalogue_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to marker catalogue JSON (default: built-in).",
)
@click.option(
    "--tolerance",
    default=0,
    show_default=True,
    help="Informational expected maximum Hamming tolerance.",
)
def gen_cmd(
    profile_path: str,
    out_path: str,
    catalogue_path: str | None,
    tolerance: int,
) -> None:
    """Enrol a DNA profile and produce enrollment artifacts."""
    catalogue = load_marker_catalogue(catalogue_path)
    profile = load_profile(profile_path)
    validate_profile(profile, catalogue)
    w = profile_to_bytes(profile, catalogue)
    cat_fp = catalogue_fingerprint(catalogue)
    key_material, enrollment = gen(w, cat_fp, tolerance=tolerance)
    save_enrollment(enrollment, out_path)
    pub_hex = public_key_bytes(
        derive_x25519_keypair(key_material, bytes.fromhex(enrollment["salt"]))[1]
    ).hex()
    click.echo(f"Enrolled: {Path(out_path)}")
    click.echo(f"Public key (hex): {pub_hex}")


main.add_command(gen_cmd, name="gen")


# ── encrypt ───────────────────────────────────────────────────────────────────


@main.command()
@click.option("--enrollment", "enr_path", required=True, type=click.Path(exists=True))
@click.option("--dna", "dna_path", required=True, type=click.Path(exists=True))
@click.option("--in", "in_path", required=True, type=click.Path(exists=True))
@click.option("--out", "out_path", required=True, type=click.Path())
@click.option("--catalogue", "catalogue_path", default=None, type=click.Path(exists=True))
def encrypt_cmd(
    enr_path: str,
    dna_path: str,
    in_path: str,
    out_path: str,
    catalogue_path: str | None,
) -> None:
    """Encrypt a file using a DNA-derived X25519 key."""
    catalogue = load_marker_catalogue(catalogue_path)
    profile = load_profile(dna_path)
    validate_profile(profile, catalogue)
    enrollment = load_enrollment(enr_path)

    w = profile_to_bytes(profile, catalogue)
    try:
        key_material = rep(w, enrollment)
    except ReconstructionError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    _, pub_key = derive_x25519_keypair(key_material, bytes.fromhex(enrollment["salt"]))
    plaintext = Path(in_path).read_bytes()
    ciphertext = encrypt(plaintext, pub_key)
    Path(out_path).write_bytes(ciphertext)
    click.echo(f"Encrypted: {out_path}")


main.add_command(encrypt_cmd, name="encrypt")


# ── decrypt ───────────────────────────────────────────────────────────────────


@main.command()
@click.option("--enrollment", "enr_path", required=True, type=click.Path(exists=True))
@click.option("--dna", "dna_path", required=True, type=click.Path(exists=True))
@click.option("--in", "in_path", required=True, type=click.Path(exists=True))
@click.option("--out", "out_path", required=True, type=click.Path())
@click.option("--catalogue", "catalogue_path", default=None, type=click.Path(exists=True))
def decrypt_cmd(
    enr_path: str,
    dna_path: str,
    in_path: str,
    out_path: str,
    catalogue_path: str | None,
) -> None:
    """Decrypt a file using a DNA-derived X25519 key."""
    catalogue = load_marker_catalogue(catalogue_path)
    profile = load_profile(dna_path)
    validate_profile(profile, catalogue)
    enrollment = load_enrollment(enr_path)

    w = profile_to_bytes(profile, catalogue)
    try:
        key_material = rep(w, enrollment)
    except ReconstructionError as exc:
        click.echo(f"Error: reconstruction failed — {exc}", err=True)
        sys.exit(1)

    priv_key, _ = derive_x25519_keypair(key_material, bytes.fromhex(enrollment["salt"]))
    try:
        from cryptography.exceptions import InvalidTag

        ciphertext = Path(in_path).read_bytes()
        plaintext = decrypt(ciphertext, priv_key)
    except InvalidTag:
        click.echo("Error: decryption authentication failed (wrong key or tampered file).", err=True)
        sys.exit(1)

    Path(out_path).write_bytes(plaintext)
    click.echo(f"Decrypted: {out_path}")


main.add_command(decrypt_cmd, name="decrypt")


# ── fuzz ──────────────────────────────────────────────────────────────────────


@main.command()
@click.option("--enrollment", "enr_path", required=True, type=click.Path(exists=True))
@click.option("--seed-profile", "seed_path", required=True, type=click.Path(exists=True))
@click.option("--out", "out_path", required=True, type=click.Path())
@click.option(
    "--snp-rates",
    default="0,0.01,0.02,0.05,0.10,0.20",
    show_default=True,
    help="Comma-separated SNP mutation rates.",
)
@click.option(
    "--str-shifts",
    default="0,1,2,3",
    show_default=True,
    help="Comma-separated STR shift magnitudes.",
)
@click.option("--n", "n_trials", default=50, show_default=True, help="Trials per condition.")
@click.option("--seed", default=42, show_default=True, type=int, help="Random seed.")
@click.option("--catalogue", "catalogue_path", default=None, type=click.Path(exists=True))
@click.option(
    "--impostors",
    "impostor_paths",
    multiple=True,
    type=click.Path(exists=True),
    help="Paths to impostor profiles (may be given multiple times).",
)
def fuzz_cmd(
    enr_path: str,
    seed_path: str,
    out_path: str,
    snp_rates: str,
    str_shifts: str,
    n_trials: int,
    seed: int,
    catalogue_path: str | None,
    impostor_paths: tuple[str, ...],
) -> None:
    """Run an adversarial fuzz campaign."""
    catalogue = load_marker_catalogue(catalogue_path)
    base_profile = load_profile(seed_path)
    validate_profile(base_profile, catalogue)
    enrollment = load_enrollment(enr_path)

    snp_rate_list = [float(x) for x in snp_rates.split(",")]
    str_shift_list = [int(x) for x in str_shifts.split(",")]

    impostors = []
    for p in impostor_paths:
        imp = load_profile(p)
        validate_profile(imp, catalogue)
        impostors.append(imp)

    results = run_campaign(
        base_profile,
        enrollment,
        catalogue,
        snp_rates=snp_rate_list,
        str_shifts=str_shift_list,
        n_trials=n_trials,
        seed=seed,
        impostor_profiles=impostors,
        out_path=out_path,
    )
    click.echo(f"Campaign complete: {len(results)} trials → {out_path}")


main.add_command(fuzz_cmd, name="fuzz")


# ── report ────────────────────────────────────────────────────────────────────


@main.command()
@click.option("--in", "in_path", required=True, type=click.Path(exists=True))
@click.option("--out", "out_dir", required=True, type=click.Path())
def report_cmd(in_path: str, out_dir: str) -> None:
    """Generate a summary JSON and plots from a JSONL campaign log."""
    results = load_results(in_path)
    metrics = compute_metrics(results)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    save_summary(metrics, summary_path)
    plots = generate_plots(metrics, out / "plots")
    click.echo(f"Summary: {summary_path}")
    click.echo(f"Plots: {[str(p) for p in plots]}")
    click.echo(json.dumps(metrics["overall"], indent=2))


main.add_command(report_cmd, name="report")


# ── experiment ────────────────────────────────────────────────────────────────


@main.command()
@click.option("--profile", "profile_path", required=True, type=click.Path(exists=True))
@click.option("--out", "out_dir", default="results", show_default=True, type=click.Path())
@click.option("--catalogue", "catalogue_path", default=None, type=click.Path(exists=True))
@click.option(
    "--impostors",
    "impostor_paths",
    multiple=True,
    type=click.Path(exists=True),
)
@click.option(
    "--snp-rates",
    default="0,0.01,0.02,0.05,0.10,0.20",
    show_default=True,
)
@click.option("--str-shifts", default="0,1,2,3", show_default=True)
@click.option("--n", "n_trials", default=50, show_default=True, type=int)
@click.option("--seed", default=42, show_default=True, type=int)
def experiment_cmd(
    profile_path: str,
    out_dir: str,
    catalogue_path: str | None,
    impostor_paths: tuple[str, ...],
    snp_rates: str,
    str_shifts: str,
    n_trials: int,
    seed: int,
) -> None:
    """Run the complete end-to-end experiment pipeline."""
    metrics = run_experiment(
        profile_path,
        catalogue_path=catalogue_path,
        impostor_profile_paths=list(impostor_paths),
        out_dir=out_dir,
        snp_rates=[float(x) for x in snp_rates.split(",")],
        str_shifts=[int(x) for x in str_shifts.split(",")],
        n_trials=n_trials,
        seed=seed,
    )
    click.echo("Experiment complete.")
    click.echo(json.dumps(metrics["overall"], indent=2))


main.add_command(experiment_cmd, name="experiment")
