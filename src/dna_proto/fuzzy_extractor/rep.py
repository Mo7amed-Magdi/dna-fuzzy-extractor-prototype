"""Fuzzy extractor Rep() — Option B secure-sketch reconstruction.

Reconstruction:
    c'  = w' XOR P
    R'  = HKDF(c', salt, info="key")
    tag' = HKDF(c', salt, info="verify")
    Accept if tag' == stored verifier_tag (constant-time comparison).

The verifier tag check ensures that:
- If w' == w  (zero noise): c' == c → tag' == tag → accept.
- If w' != w  (noise present): c' != c → tag' != tag → reject.

Without ECC, reconstruction succeeds only when the encoded vector is
bit-for-bit identical to the enrollment vector.  Tolerance at the system
level comes from STR quantization at the encoding stage.
"""

from __future__ import annotations

import hmac

from ..kdf_keys.kdf import hkdf_derive


class ReconstructionError(Exception):
    """Raised when Rep() rejects the biometric sample."""


def rep(w_prime: bytes, enrollment: dict) -> bytes:
    """Run reconstruction (Rep) for a biometric vector.

    Parameters
    ----------
    w_prime:
        Biometric feature vector from the new (possibly noisy) sample.
    enrollment:
        Enrollment artifact dict (loaded from file via ``load_enrollment``).

    Returns
    -------
    32 bytes of key material (same as Gen output for a matching sample).

    Raises
    ------
    ReconstructionError
        If the verifier tag does not match (w' is too different from w).
    ValueError
        If the enrollment artifact is malformed or the vector length differs.
    """
    n = enrollment["n_bytes"]
    if len(w_prime) != n:
        raise ValueError(
            f"Biometric vector length mismatch: expected {n} bytes, got {len(w_prime)}."
        )

    P = bytes.fromhex(enrollment["helper_data"])
    stored_tag = bytes.fromhex(enrollment["verifier_tag"])
    salt = bytes.fromhex(enrollment["salt"])

    # Candidate secret seed: c' = w' XOR P
    c_prime = bytes(wpi ^ Pi for wpi, Pi in zip(w_prime, P))

    # Derive candidate key material and verifier tag
    candidate_key = hkdf_derive(c_prime, salt, info=b"dna-proto-key", length=32)
    candidate_tag = hkdf_derive(c_prime, salt, info=b"dna-proto-verify", length=32)

    # Constant-time comparison to prevent timing side-channels
    if not hmac.compare_digest(candidate_tag, stored_tag):
        raise ReconstructionError(
            "Reconstruction failed: biometric sample does not match enrollment."
        )

    return candidate_key
