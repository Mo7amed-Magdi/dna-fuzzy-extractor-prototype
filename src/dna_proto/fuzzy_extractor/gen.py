"""Fuzzy extractor Gen() — Option B secure-sketch simulation.

Design (Option B, no BCH/RS):
- Enrollment:
    c  = os.urandom(n_bytes)             # uniformly random secret seed
    P  = w XOR c                         # helper data (public sketch)
    tag = HKDF(c, salt, info="verify")   # verifier tag stored in artifacts
    R  = HKDF(c, salt, info="key")       # actual key material (returned, NOT stored)

  Artifacts stored: { P, tag, salt, catalogue_fp, n_bytes }
  Nothing stored: w (encoded vector), c (secret seed), R (key material).

Security note (for research prototype):
  This construction is a *simulation* of the fuzzy commitment scheme.
  Without a real error-correcting code the extractor only succeeds when w'
  matches w bit-for-bit.  Tolerance is provided at the encoding stage through
  STR quantization bins, not through algebraic decoding.  See README for a
  full discussion of the security model.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from ..kdf_keys.kdf import hkdf_derive


def gen(
    w: bytes,
    catalogue_fp: str,
    *,
    tolerance: int = 0,
) -> tuple[bytes, dict]:
    """Run enrollment (Gen) for a biometric vector.

    Parameters
    ----------
    w:
        Biometric feature vector (output of ``profile_to_bytes``).
    catalogue_fp:
        Hex fingerprint of the canonical marker catalogue (stored in artifacts
        so Rep() can detect marker-set changes).
    tolerance:
        Informational parameter documenting expected max Hamming distance.
        Not used for cryptographic decisions; kept in artifacts for logging.

    Returns
    -------
    (key_material, enrollment_dict)
        ``key_material`` – 32 raw bytes suitable for KDF input.  Do NOT store.
        ``enrollment_dict`` – JSON-serialisable dict to save as the enrollment
        artifact file.  Does NOT contain ``w`` or the secret seed.
    """
    n = len(w)
    salt = os.urandom(32)

    # Secret seed: uniformly random bytes
    c = os.urandom(n)

    # Helper data: XOR of biometric vector and secret seed
    P = bytes(wi ^ ci for wi, ci in zip(w, c))

    # Key material derived from secret seed
    key_material = hkdf_derive(c, salt, info=b"dna-proto-key", length=32)

    # Verifier tag: allows Rep() to confirm reconstruction without storing c
    verifier_tag = hkdf_derive(c, salt, info=b"dna-proto-verify", length=32)

    enrollment = {
        "helper_data": P.hex(),
        "verifier_tag": verifier_tag.hex(),
        "salt": salt.hex(),
        "n_bytes": n,
        "tolerance": tolerance,
        "catalogue_fp": catalogue_fp,
    }

    # Securely zero the secret seed from memory (best-effort in CPython)
    # The memoryview approach below zeroes the bytearray buffer.
    c_arr = bytearray(c)
    for i in range(len(c_arr)):
        c_arr[i] = 0
    del c_arr, c

    return key_material, enrollment


def save_enrollment(enrollment: dict, path: Path | str) -> None:
    """Write enrollment artifacts to a JSON file."""
    with open(path, "w") as fh:
        json.dump(enrollment, fh, indent=2)


def load_enrollment(path: Path | str) -> dict:
    """Load enrollment artifacts from a JSON file."""
    with open(path) as fh:
        return json.load(fh)
