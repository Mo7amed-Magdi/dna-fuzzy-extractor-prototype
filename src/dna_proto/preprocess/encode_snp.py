"""SNP nucleotide → 2-bit encoding."""

from __future__ import annotations

# Fixed mapping: A=00, C=01, G=10, T=11
SNP_ENCODING: dict[str, int] = {"A": 0b00, "C": 0b01, "G": 0b10, "T": 0b11}
SNP_DECODING: dict[int, str] = {v: k for k, v in SNP_ENCODING.items()}


def encode_snp(base: str) -> int:
    """Encode a single SNP nucleotide to a 2-bit integer.

    Parameters
    ----------
    base:
        One of ``A``, ``C``, ``G``, ``T``.

    Returns
    -------
    Integer in ``[0, 3]``.
    """
    b = base.upper()
    if b not in SNP_ENCODING:
        raise ValueError(f"Invalid SNP base '{base}'. Must be one of A, C, G, T.")
    return SNP_ENCODING[b]


def decode_snp(bits: int) -> str:
    """Decode a 2-bit integer back to a nucleotide character."""
    if bits not in SNP_DECODING:
        raise ValueError(f"Invalid SNP bit value {bits}. Must be in [0, 3].")
    return SNP_DECODING[bits]


def encode_snp_list(bases: list[str]) -> list[int]:
    """Encode a list of SNP bases to a list of 2-bit integers."""
    return [encode_snp(b) for b in bases]
