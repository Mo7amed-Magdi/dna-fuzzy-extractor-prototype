"""STR repeat-count → quantized n-bit encoding."""

from __future__ import annotations

import math
from typing import Any


def _n_bins(n_bits: int) -> int:
    return 2**n_bits


def encode_str(value: int, min_val: int, max_val: int, n_bits: int) -> int:
    """Quantize an STR repeat count to an n-bit integer.

    The range ``[min_val, max_val]`` is divided into ``2**n_bits`` equal-width
    bins.  Values that differ by at most ``floor(range / n_bins)`` repeats may
    land in the same bin, providing inherent tolerance.

    Parameters
    ----------
    value:
        Raw repeat count (integer).
    min_val, max_val:
        Inclusive bounds for the marker (from the catalogue).
    n_bits:
        Number of bits used for quantization (controls precision/tolerance).

    Returns
    -------
    Integer in ``[0, 2**n_bits - 1]``.
    """
    if value < min_val or value > max_val:
        raise ValueError(
            f"STR value {value} out of range [{min_val}, {max_val}]"
        )
    n_bins = _n_bins(n_bits)
    span = max_val - min_val
    # Bin index: clamp to [0, n_bins-1]
    if span == 0:
        return 0
    bin_index = int(math.floor((value - min_val) * n_bins / (span + 1)))
    return min(bin_index, n_bins - 1)


def decode_str_bin(bin_index: int, min_val: int, max_val: int, n_bits: int) -> int:
    """Decode a bin index back to the midpoint repeat count (approximate)."""
    n_bins = _n_bins(n_bits)
    span = max_val - min_val
    step = (span + 1) / n_bins
    return int(min_val + (bin_index + 0.5) * step)


def encode_str_markers(
    str_values: dict[str, int],
    str_entries: list[dict[str, Any]],
) -> list[tuple[str, int, int]]:
    """Encode all STR markers in catalogue order.

    Parameters
    ----------
    str_values:
        Mapping of marker id to repeat count.
    str_entries:
        Ordered list of STR entry dicts from the marker catalogue.

    Returns
    -------
    List of ``(marker_id, bin_index, n_bits)`` tuples in catalogue order.
    """
    result = []
    for entry in str_entries:
        mid = entry["id"]
        val = str_values[mid]
        bin_idx = encode_str(val, entry["min"], entry["max"], entry["n_bits"])
        result.append((mid, bin_idx, entry["n_bits"]))
    return result
