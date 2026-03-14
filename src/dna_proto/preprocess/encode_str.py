"""STR repeat-count quantization encoding.

STR repeat counts in [5, 30] are quantized into 4-bit bins:
    bin = min(15, (count - STR_MIN) // 2)

This gives tolerance: adjacent even/odd repeat counts often map to the same bin,
reducing sensitivity to ±1 measurement variation.
"""

from __future__ import annotations

from dna_proto.dna_input.schema import STR_MAX, STR_MIN

STR_BITS: int = 4
STR_BIN_WIDTH: int = 2
MAX_BIN: int = (1 << STR_BITS) - 1  # 15


def encode_str(count: int) -> int:
    """Encode an STR repeat count to a 4-bit bin integer (0–15).

    Counts outside [STR_MIN, STR_MAX] are clamped before encoding.
    """
    clamped = max(STR_MIN, min(STR_MAX, count))
    return min(MAX_BIN, (clamped - STR_MIN) // STR_BIN_WIDTH)


def decode_str_approx(bin_value: int) -> int:
    """Decode a bin index back to an approximate repeat count (lower bound of bin)."""
    if not (0 <= bin_value <= MAX_BIN):
        raise ValueError(f"Invalid STR bin {bin_value!r}; must be 0–{MAX_BIN}")
    return STR_MIN + bin_value * STR_BIN_WIDTH


def encode_str_list(counts: list[int]) -> list[int]:
    """Encode a list of STR repeat counts to 4-bit bin integers."""
    return [encode_str(c) for c in counts]
