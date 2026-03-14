"""Vectorize a DNAProfile into a deterministic binary biometric vector.

Layout:
  - 256 SNP markers × 2 bits each  = 512 bits
  - 64  STR markers × 4 bits each  = 256 bits
  Total                             = 768 bits = 96 bytes

The marker ordering is determined by the sorted marker ID list.
The same ordering must be used for both enrollment and reconstruction.
"""

from __future__ import annotations

N_SNPS: int = 256
N_STRS: int = 64
SNP_BITS: int = 2
STR_BITS: int = 4
BIOMETRIC_BITS: int = N_SNPS * SNP_BITS + N_STRS * STR_BITS  # 768
BIOMETRIC_BYTES: int = BIOMETRIC_BITS // 8  # 96


def _pack_bits(bit_values: list[int], bits_per_value: int) -> bytes:
    """Pack a list of fixed-width integers into a compact byte string."""
    total_bits = len(bit_values) * bits_per_value
    buf = bytearray((total_bits + 7) // 8)
    for i, val in enumerate(bit_values):
        for b in range(bits_per_value - 1, -1, -1):
            bit_pos = i * bits_per_value + (bits_per_value - 1 - b)
            if val & (1 << b):
                buf[bit_pos // 8] |= 1 << (7 - (bit_pos % 8))
    return bytes(buf)


def vectorize(profile: "dna_proto.dna_input.schema.DNAProfile") -> bytes:
    """Convert a DNAProfile to a 96-byte biometric vector.

    The profile must contain exactly N_SNPS SNPs and N_STRS STRs.
    Marker IDs are sorted lexicographically to guarantee determinism.

    Raises ValueError if the profile has the wrong number of markers.
    """
    from dna_proto.preprocess.encode_snp import encode_snp
    from dna_proto.preprocess.encode_str import encode_str

    n_snps = len(profile.snps)
    n_strs = len(profile.strs)
    if n_snps != N_SNPS:
        raise ValueError(f"Expected {N_SNPS} SNPs, got {n_snps}")
    if n_strs != N_STRS:
        raise ValueError(f"Expected {N_STRS} STRs, got {n_strs}")

    snp_values = [encode_snp(profile.snps[k]) for k in sorted(profile.snps)]
    str_values = [encode_str(profile.strs[k]) for k in sorted(profile.strs)]

    snp_bytes = _pack_bits(snp_values, SNP_BITS)  # 64 bytes
    str_bytes = _pack_bits(str_values, STR_BITS)   # 32 bytes
    biometric = snp_bytes + str_bytes              # 96 bytes
    assert len(biometric) == BIOMETRIC_BYTES, (
        f"Biometric length mismatch: {len(biometric)} != {BIOMETRIC_BYTES}"
    )
    return biometric


def hamming_distance(a: bytes, b: bytes) -> int:
    """Compute the bit-level Hamming distance between two byte strings."""
    if len(a) != len(b):
        raise ValueError("Byte strings must have equal length")
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))
