# DNA Fuzzy Extractor Research Prototype

> ⚠️ **Ethics & Security Disclaimer** — Read before use ⚠️

This is a **research prototype only**. It must not be used in production
systems or with real human DNA data without independent security review.
DNA data is uniquely identifying, permanent, and sensitive.  It cannot be
revoked if compromised.  Additional considerations:

- This implementation uses a **simulation** of the fuzzy-commitment scheme
  (Option B, no BCH/Reed–Solomon).  Without a real algebraic error-correcting
  code, exact bit-level matching is required at the extractor layer; tolerance
  is provided through STR quantization at the encoding stage only.
- The security analysis (min-entropy, helper-data leakage, collision bounds)
  has not been formally verified.  Claims are experimental.
- Relatives share DNA markers, elevating the real-world FAR.  The impostor
  profiles in `data/` are independently generated synthetic data and do not
  model relatedness.
- Synthetic data in `data/` are generated from a fixed PRNG seed and carry no
  biological meaning.
- **Never** input real genomic data or link this system to actual individuals.

---

## What this prototype does

```
DNA markers (SNP/STR)
       │ load & validate
       ▼
  Feature vector (bytes)
       │ Gen()
       ▼
  Helper data P  ──────────────────────┐ (public, stored in enrollment.json)
  Key material R  ─► HKDF ─► X25519 keypair
       │                         │
       │         Rep()           │
   w' (noisy) ─► c' = w' ⊕ P ─► HKDF ─► key' == R ?
                                         ↓ yes: same keypair
                         hybrid encrypt/decrypt (ephemeral X25519 + ChaCha20-Poly1305)
```

Full pipeline:

1. **DNA input** — load SNP/STR marker profiles from JSON or CSV.
2. **Preprocessing** — SNP→2 bits (A=00 C=01 G=10 T=11), STR→quantized n bits.
3. **Fuzzy extractor (Option B)**
   - *Gen*: `c = random_bytes`, `P = w ⊕ c`, verifier tag stored.
   - *Rep*: `c' = w' ⊕ P`, verify via HKDF-derived tag.
4. **KDF → X25519** — HKDF-SHA256 from secret seed → deterministic Curve25519 keypair.
5. **Hybrid encryption** — ephemeral X25519 ECDH + ChaCha20-Poly1305 AEAD.
6. **Adversarial fuzzing** — SNP substitution, STR shift, bit-flip, boundary tests.
7. **Evaluation** — FRR, FAR, success rate, Hamming statistics, JSONL logs, plots.
8. **Experiment controller** — automated end-to-end pipeline with reporting.

---

## Quickstart

### Requirements

- Python ≥ 3.10
- Dependencies: `cryptography`, `click`, `matplotlib`

### Installation

```bash
git clone https://github.com/Mo7amed-Magdi/dna-fuzzy-extractor-prototype
cd dna-fuzzy-extractor-prototype
pip install -e ".[dev]"
```

### Enrol a subject

```bash
dna-proto gen \
  --in data/synthetic_profiles/subject_001.json \
  --out enrollment_001.json
```

### Encrypt a file

```bash
dna-proto encrypt \
  --enrollment enrollment_001.json \
  --dna data/synthetic_profiles/subject_001.json \
  --in secret.txt \
  --out secret.txt.enc
```

### Decrypt a file

```bash
dna-proto decrypt \
  --enrollment enrollment_001.json \
  --dna data/synthetic_profiles/subject_001.json \
  --in secret.txt.enc \
  --out secret_recovered.txt
```

Decryption with a different subject's DNA will fail (reconstruction error).

### Run a fuzz campaign

```bash
dna-proto fuzz \
  --enrollment enrollment_001.json \
  --seed-profile data/synthetic_profiles/subject_001.json \
  --out results/campaign.jsonl \
  --snp-rates 0,0.01,0.02,0.05,0.10,0.20 \
  --str-shifts 0,1,2,3 \
  --n 100 \
  --impostors data/synthetic_profiles/subject_002.json \
  --impostors data/synthetic_profiles/subject_003.json
```

### Generate a report with plots

```bash
dna-proto report \
  --in results/campaign.jsonl \
  --out results/report
```

### Run the complete experiment pipeline

```bash
dna-proto experiment \
  --profile data/synthetic_profiles/subject_001.json \
  --out results/ \
  --impostors data/synthetic_profiles/subject_002.json \
  --snp-rates 0,0.01,0.05,0.10,0.20 \
  --str-shifts 0,1,2,3 \
  --n 100
```

### Run tests

```bash
pytest
```

---

## Project layout

```
dna-fuzzy-extractor-prototype/
├── pyproject.toml
├── README.md
├── .github/workflows/ci.yml
├── src/dna_proto/
│   ├── cli.py                      ← dna-proto CLI entry point
│   ├── dna_input/
│   │   ├── loader.py               ← JSON/CSV profile loader
│   │   └── schema.py               ← marker catalogue + validation
│   ├── preprocess/
│   │   ├── encode_snp.py           ← SNP → 2-bit encoding
│   │   ├── encode_str.py           ← STR → quantized n-bit encoding
│   │   └── vectorize.py            ← concat to bytes, Hamming distance
│   ├── fuzzy_extractor/
│   │   ├── gen.py                  ← Gen(): P = w ⊕ c, verifier tag
│   │   └── rep.py                  ← Rep(): c' = w' ⊕ P, verify tag
│   ├── kdf_keys/
│   │   ├── kdf.py                  ← HKDF-SHA256
│   │   └── x25519_keys.py          ← deterministic X25519 keypair
│   ├── crypto/
│   │   └── hybrid_encrypt.py       ← ephemeral X25519 + ChaCha20-Poly1305
│   ├── fuzzing/
│   │   ├── mutators.py             ← SNP substitution, STR shift, bit-flip
│   │   └── campaign.py             ← systematic fuzz campaign + JSONL log
│   ├── evaluation/
│   │   ├── metrics.py              ← FRR, FAR, success rate, Hamming stats
│   │   └── report.py               ← summary JSON + matplotlib plots
│   └── controller/
│       └── experiment.py           ← end-to-end experiment pipeline
├── data/
│   ├── synthetic_markers.json      ← 256 SNPs + 32 STRs marker catalogue
│   └── synthetic_profiles/
│       ├── subject_001.json        ← 10 synthetic subject profiles
│       ├── subject_001.csv         ← same profile in CSV format
│       └── ...
└── tests/                          ← 87 pytest tests
```

---

## CLI reference

| Command | Description |
|---------|-------------|
| `dna-proto gen` | Enrol a DNA profile; output enrollment artifact |
| `dna-proto encrypt` | Encrypt a file using a DNA-derived key |
| `dna-proto decrypt` | Decrypt a file using a DNA-derived key |
| `dna-proto fuzz` | Run an adversarial fuzz campaign |
| `dna-proto report` | Generate summary JSON + plots from a JSONL log |
| `dna-proto experiment` | Run the full end-to-end pipeline |

Run `dna-proto <command> --help` for per-command options.

---

## Security model summary

| Property | Status |
|----------|--------|
| Enrollment stores raw DNA | ❌ Never |
| Enrollment stores encoded vector | ❌ Never |
| Helper data reveals DNA | Partially (sim.); no formal bound |
| Key reproducible from same DNA | ✅ |
| Key different from different DNA | ✅ (all test impostors rejected) |
| Error tolerance (FE layer) | ❌ Simulation only; see note |
| Error tolerance (encoding layer) | ✅ STR quantization bins |
| AEAD authenticated encryption | ✅ ChaCha20-Poly1305 |
| Forward secrecy | ✅ Ephemeral X25519 sender key |
