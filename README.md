# DNA Fuzzy Extractor Prototype

> **⚠️ DISCLAIMER – Research Prototype Only**
> This software is a *research and educational prototype*. It is **not** production-ready
> and must **not** be used with real human DNA data. DNA is highly identifying and
> sensitive. No real genomic data is processed; all inputs are synthetic simulations.
> Cryptographic security claims are experimental and have not been formally proven.

---

## Overview

This prototype demonstrates a complete pipeline for deriving cryptographic keys from
synthetic DNA biometric features (SNPs and STRs) using a **fuzzy extractor** construction.
It evaluates system robustness under adversarial fuzzing.

### Pipeline

```
DNA profile (JSON/CSV)
    │
    ▼
Feature preprocessing  (SNP: A/C/G/T → 2-bit; STR: repeat-count → 4-bit)
    │
    ▼
Biometric vector  (768 bits = 96 bytes)
    │
    ├─ Gen()  ──►  helper data (sketch, salt, verifier, public key)
    │              [stored; never stores raw DNA or secret]
    │
    ▼
Fuzzy extractor Rep()  ← noisy query biometric + helper data
    │
    ▼
Recovered secret  →  HKDF-SHA256  →  X25519 keypair
    │
    ▼
Hybrid encryption  (ephemeral X25519 DH + ChaCha20-Poly1305)
```

### Fuzzy Extractor — Option B (secure-sketch simulation)

Instead of a full BCH/Reed–Solomon implementation, this prototype uses a
**rate-1/3 repetition code** as a secure sketch simulation:

- Secret `s`: 32 random bytes (256 bits)
- Codeword `c = rep3(s)`: each bit of `s` repeated 3 times → 768 bits
- Helper data: `sketch = biometric XOR codeword`
- Recovery: `noisy_codeword = new_biometric XOR sketch`, then majority-vote per 3-bit group
- Error correction capacity: 1 bit per 3-bit group (tolerates ~33% local noise)

---

## Quickstart

### Install

```bash
pip install -e ".[dev]"
```

### Generate synthetic data

```bash
python -m dna_proto.data_gen.generate_synthetic
```

### Enroll a DNA profile

```bash
dna-proto gen --in data/synthetic_profiles/subject_001.json --out enrollment.json
```

### Encrypt a file

```bash
echo "secret medical record" > plaintext.txt
dna-proto encrypt \
    --enrollment enrollment.json \
    --dna data/synthetic_profiles/subject_001.json \
    --in plaintext.txt \
    --out ciphertext.enc
```

### Decrypt

```bash
dna-proto decrypt \
    --enrollment enrollment.json \
    --dna data/synthetic_profiles/subject_001.json \
    --in ciphertext.enc \
    --out recovered.txt
cat recovered.txt
```

### Run adversarial fuzzing campaign

```bash
dna-proto fuzz-campaign \
    --enrollment enrollment.json \
    --seed data/synthetic_profiles/subject_001.json \
    --impostors data/synthetic_profiles \
    --levels 0,1,2,4,8,16 \
    --n 200 \
    --out results/campaign.jsonl
```

### Generate report + plots

```bash
dna-proto report --in results/campaign.jsonl --out results/
```

### Run all tests

```bash
pytest
```

---

## Marker format (JSON)

```json
{
  "subject_id": "S001",
  "snps": {
    "rs0001": "A",
    "rs0002": "G"
  },
  "strs": {
    "str_001": 15,
    "str_002": 17
  }
}
```

- `snps`: dict of marker ID → nucleotide (`A`, `C`, `G`, `T`)
- `strs`: dict of marker ID → integer repeat count in `[5, 30]`

---

## Evaluation metrics

| Metric | Description |
|--------|-------------|
| **FRR** | False Rejection Rate – genuine queries rejected |
| **FAR** | False Acceptance Rate – impostor queries accepted |
| **Success rate** | Fraction of genuine queries that succeed |
| **Key collision** | Fraction of impostors producing same public key |

---

## Project structure

```
src/dna_proto/
  cli.py                 CLI entry point
  dna_input/             DNA profile loading and validation
  preprocess/            SNP/STR encoding to biometric vector
  fuzzy_extractor/       Gen() / Rep() with rep-3 secure sketch
  kdf_keys/              HKDF-SHA256 + deterministic X25519
  crypto/                Hybrid encryption (X25519 + ChaCha20-Poly1305)
  fuzzing/               Mutation strategies + campaign runner
  evaluation/            Metrics + plot/report generation
  controller/            End-to-end experiment orchestrator
  data_gen/              Synthetic profile generator
data/                    Sample synthetic profiles
results/                 Experiment outputs
tests/                   pytest test suite
```

---

## Security notes

1. **Helper data leakage**: the sketch reveals information about the biometric vector.
2. **Revocability**: DNA cannot be revoked. Helper data exposure is irreversible.
3. **Relatedness**: related individuals share markers, increasing FAR.
4. **Min-entropy**: security requires sufficient unpredictability in the marker set.
5. **Not for production**: this prototype omits robustness against active adversaries,
   side-channel mitigations, and secure memory erasure.