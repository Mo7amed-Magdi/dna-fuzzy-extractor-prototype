"""CLI entry point for the DNA Fuzzy Extractor Prototype."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from dna_proto.dna_input.loader import load_profile
from dna_proto.dna_input.schema import validate_profile
from dna_proto.evaluation.report import generate_report, load_jsonl, save_jsonl
from dna_proto.fuzzy_extractor.gen import gen
from dna_proto.fuzzy_extractor.rep import rep
from dna_proto.fuzzing.campaign import run_campaign
from dna_proto.kdf_keys.x25519_keys import public_key_from_bytes
from dna_proto.preprocess.vectorize import vectorize


@click.group()
@click.version_option(package_name="dna-proto")
def main() -> None:
    """DNA Fuzzy Extractor Prototype.

    \b
    DISCLAIMER: Research prototype only. Use synthetic data exclusively.
    Do NOT use with real human genomic data.
    """


# ---------------------------------------------------------------------------
# gen command
# ---------------------------------------------------------------------------

@main.command("gen")
@click.option(
    "--in", "input_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="DNA profile JSON or CSV file.",
)
@click.option(
    "--out", "output_file",
    required=True,
    type=click.Path(dir_okay=False),
    help="Output enrollment JSON file (helper data only – no raw DNA).",
)
def cmd_gen(input_file: str, output_file: str) -> None:
    """Enroll a DNA profile and generate helper data."""
    profile = load_profile(input_file)
    biometric = vectorize(profile)
    _secret, helper_data = gen(biometric)

    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(helper_data, fh, indent=2)
    click.echo(f"Enrollment helper data written to {output_file}")
    click.echo(f"  Public key: {helper_data['public_key'][:16]}…")


# ---------------------------------------------------------------------------
# encrypt command
# ---------------------------------------------------------------------------

@main.command("encrypt")
@click.option(
    "--enrollment", required=True, type=click.Path(exists=True, dir_okay=False),
    help="Enrollment JSON file produced by 'gen'.",
)
@click.option(
    "--dna", required=True, type=click.Path(exists=True, dir_okay=False),
    help="DNA profile to use for key reconstruction.",
)
@click.option(
    "--in", "input_file", required=True, type=click.Path(exists=True, dir_okay=False),
    help="Plaintext file to encrypt.",
)
@click.option(
    "--out", "output_file", required=True, type=click.Path(dir_okay=False),
    help="Output encrypted JSON file.",
)
def cmd_encrypt(
    enrollment: str, dna: str, input_file: str, output_file: str
) -> None:
    """Encrypt a file using the DNA-derived public key."""
    from dna_proto.crypto.hybrid_encrypt import encrypt as do_encrypt

    with open(enrollment, encoding="utf-8") as fh:
        helper_data = json.load(fh)

    public_key = public_key_from_bytes(bytes.fromhex(helper_data["public_key"]))

    plaintext = Path(input_file).read_bytes()
    packet = do_encrypt(public_key, plaintext)

    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(packet, fh, indent=2)
    click.echo(f"Encrypted → {output_file}  ({len(plaintext)} bytes plaintext)")


# ---------------------------------------------------------------------------
# decrypt command
# ---------------------------------------------------------------------------

@main.command("decrypt")
@click.option(
    "--enrollment", required=True, type=click.Path(exists=True, dir_okay=False),
    help="Enrollment JSON file produced by 'gen'.",
)
@click.option(
    "--dna", required=True, type=click.Path(exists=True, dir_okay=False),
    help="DNA profile for key reconstruction (may be a new/noisy sample).",
)
@click.option(
    "--in", "input_file", required=True, type=click.Path(exists=True, dir_okay=False),
    help="Encrypted JSON file produced by 'encrypt'.",
)
@click.option(
    "--out", "output_file", required=True, type=click.Path(dir_okay=False),
    help="Output decrypted file.",
)
def cmd_decrypt(
    enrollment: str, dna: str, input_file: str, output_file: str
) -> None:
    """Decrypt a file using DNA-reconstructed private key."""
    from dna_proto.crypto.hybrid_encrypt import decrypt as do_decrypt

    with open(enrollment, encoding="utf-8") as fh:
        helper_data = json.load(fh)

    profile = load_profile(dna)
    biometric = vectorize(profile)
    _key, private_key, success = rep(biometric, helper_data)

    if not success or private_key is None:
        click.echo("Key reconstruction FAILED – DNA sample too different from enrollment.")
        sys.exit(1)

    with open(input_file, encoding="utf-8") as fh:
        packet = json.load(fh)

    try:
        plaintext = do_decrypt(private_key, packet)
    except Exception as exc:
        click.echo(f"Decryption failed: {exc}")
        sys.exit(1)

    Path(output_file).write_bytes(plaintext)
    click.echo(f"Decrypted → {output_file}  ({len(plaintext)} bytes)")


# ---------------------------------------------------------------------------
# fuzz-campaign command
# ---------------------------------------------------------------------------

@main.command("fuzz-campaign")
@click.option(
    "--enrollment", required=True, type=click.Path(exists=True, dir_okay=False),
    help="Enrollment JSON file.",
)
@click.option(
    "--seed", "seed_dna", required=True, type=click.Path(exists=True, dir_okay=False),
    help="Seed DNA profile (the enrolled subject).",
)
@click.option(
    "--impostors", required=False, default=None, type=click.Path(exists=True),
    help="Directory of impostor DNA profiles (JSON files).",
)
@click.option(
    "--levels", default="0,1,2,4,8,16",
    help="Comma-separated list of SNP mutation counts (default: 0,1,2,4,8,16).",
)
@click.option(
    "--n", "n_trials", default=200, type=int,
    help="Genuine trials per mutation level (default: 200).",
)
@click.option(
    "--out", "output_file", required=True, type=click.Path(dir_okay=False),
    help="Output JSONL file for raw results.",
)
def cmd_fuzz_campaign(
    enrollment: str,
    seed_dna: str,
    impostors: str | None,
    levels: str,
    n_trials: int,
    output_file: str,
) -> None:
    """Run adversarial fuzzing campaign against enrolled helper data."""
    with open(enrollment, encoding="utf-8") as fh:
        helper_data = json.load(fh)

    with open(seed_dna, encoding="utf-8") as fh:
        seed_profile_dict = json.load(fh)

    impostor_dicts: list[dict] = []
    if impostors:
        imp_dir = Path(impostors)
        for p in sorted(imp_dir.glob("*.json")):
            if p.resolve() != Path(seed_dna).resolve():
                with open(p, encoding="utf-8") as fh:
                    impostor_dicts.append(json.load(fh))

    mutation_levels = [int(x.strip()) for x in levels.split(",")]

    click.echo(
        f"Running campaign: {len(mutation_levels)} levels × {n_trials} trials, "
        f"{len(impostor_dicts)} impostors …"
    )
    results = run_campaign(
        seed_profile_dict=seed_profile_dict,
        helper_data=helper_data,
        impostor_dicts=impostor_dicts,
        mutation_levels=mutation_levels,
        n_trials_per_level=n_trials,
    )

    save_jsonl(results, output_file)
    click.echo(f"Wrote {len(results)} results to {output_file}")


# ---------------------------------------------------------------------------
# report command
# ---------------------------------------------------------------------------

@main.command("report")
@click.option(
    "--in", "input_file", required=True, type=click.Path(exists=True, dir_okay=False),
    help="JSONL results file from 'fuzz-campaign'.",
)
@click.option(
    "--out", "output_dir", required=True, type=click.Path(),
    help="Output directory for report files and plots.",
)
def cmd_report(input_file: str, output_dir: str) -> None:
    """Generate summary report and plots from campaign results."""
    results = load_jsonl(input_file)
    metrics = generate_report(results, output_dir)

    click.echo("=== Summary ===")
    click.echo(f"  Genuine trials : {metrics['n_genuine']}")
    click.echo(f"  Impostor trials: {metrics['n_impostor']}")
    click.echo(f"  Success rate   : {metrics['success_rate']:.4f}")
    click.echo(f"  FRR            : {metrics['frr']:.4f}")
    click.echo(f"  FAR            : {metrics['far']:.4f}")
    click.echo(f"  Key collisions : {metrics['key_collision_rate']:.4f}")
    click.echo(f"Report written to {output_dir}/")
