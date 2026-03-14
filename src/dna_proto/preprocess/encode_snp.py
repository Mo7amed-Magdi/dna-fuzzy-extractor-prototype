"""SNP nucleotide encoding: A=00, C=01, G=10, T=11."""

from __future__ import annotations

# Fixed mapping — must never change; changing breaks all enrollments
SNP_MAP: dict[str, int] = {
    "A": 0b00,
    "C": 0b01,
    "G": 0b10,
    "T": 0b11,
}

INV_SNP_MAP: dict[int, str] = {v: k for k, v in SNP_MAP.items()}


def encode_snp(nucleotide: str) -> int:
    """Encode a single SNP nucleotide to a 2-bit integer (0–3)."""
    nucleotide = nucleotide.upper()
    if nucleotide not in SNP_MAP:
        raise ValueError(f"Invalid nucleotide {nucleotide!r}; must be one of A, C, G, T")
    return SNP_MAP[nucleotide]


def decode_snp(value: int) -> str:
    """Decode a 2-bit integer (0–3) back to a nucleotide string."""
    if value not in INV_SNP_MAP:
        raise ValueError(f"Invalid SNP value {value!r}; must be 0–3")
    return INV_SNP_MAP[value]


def encode_snp_list(nucleotides: list[str]) -> list[int]:
    """Encode a list of SNP nucleotides to a list of 2-bit integers."""
    return [encode_snp(n) for n in nucleotides]
