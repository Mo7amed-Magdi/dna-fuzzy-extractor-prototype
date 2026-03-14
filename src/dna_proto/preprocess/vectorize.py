"""Vectorization: convert encoded SNP/STR markers to a bytes object."""

from __future__ import annotations

import hashlib
from typing import Any

from .encode_snp import encode_snp_list
from .encode_str import encode_str_markers


def profile_to_bytes(
    profile: dict[str, Any],
    catalogue: dict[str, Any],
) -> bytes:
    """Convert a validated DNA profile to a deterministic byte vector.

    Encoding order follows the canonical marker catalogue so the same profile
    always produces the same bytes regardless of dict ordering.

    Layout (bitstring, packed into bytes, MSB first):
    - For each SNP in catalogue order: 2 bits (A=00, C=01, G=10, T=11)
    - For each STR in catalogue order: n_bits bits (quantized bin index)
    - Zero-pad the final byte if necessary.

    Parameters
    ----------
    profile:
        Validated profile dict with ``snps`` and ``strs``.
    catalogue:
        Canonical marker catalogue.

    Returns
    -------
    ``bytes`` object representing the biometric feature vector.
    """
    snp_ids: list[str] = catalogue["snp_markers"]
    str_entries: list[dict[str, Any]] = catalogue["str_markers"]

    # Encode SNPs (2 bits each)
    snp_values = [profile["snps"][sid] for sid in snp_ids]
    snp_ints = encode_snp_list(snp_values)

    # Encode STRs (n_bits each)
    str_encoded = encode_str_markers(profile["strs"], str_entries)

    # Build a bit list
    bits: list[int] = []
    for val in snp_ints:
        bits.append((val >> 1) & 1)
        bits.append(val & 1)
    for _, bin_idx, n_bits in str_encoded:
        for shift in range(n_bits - 1, -1, -1):
            bits.append((bin_idx >> shift) & 1)

    # Pack bits into bytes (MSB first, zero-pad last byte)
    n_bytes = (len(bits) + 7) // 8
    result = bytearray(n_bytes)
    for i, bit in enumerate(bits):
        if bit:
            result[i // 8] |= 1 << (7 - (i % 8))

    return bytes(result)


def vector_length_bits(catalogue: dict[str, Any]) -> int:
    """Return the total number of bits in the encoded vector for a catalogue."""
    n_snp_bits = 2 * len(catalogue["snp_markers"])
    n_str_bits = sum(e["n_bits"] for e in catalogue["str_markers"])
    return n_snp_bits + n_str_bits


def hamming_distance(a: bytes, b: bytes) -> int:
    """Compute bitwise Hamming distance between two equal-length byte strings."""
    if len(a) != len(b):
        raise ValueError("Byte strings must have equal length for Hamming distance")
    count = 0
    for x, y in zip(a, b):
        xor = x ^ y
        # Count set bits (Kernighan's method)
        while xor:
            count += xor & 1
            xor >>= 1
    return count


def catalogue_fingerprint(catalogue: dict[str, Any]) -> str:
    """Return a short hex fingerprint of the canonical marker order.

    This is stored in enrollment artifacts so Rep() can detect marker-set
    mismatches.
    """
    snp_part = ",".join(catalogue["snp_markers"])
    str_part = ",".join(
        f"{e['id']}:{e['min']}:{e['max']}:{e['n_bits']}"
        for e in catalogue["str_markers"]
    )
    raw = f"snps={snp_part};strs={str_part}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]
