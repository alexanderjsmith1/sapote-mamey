# Public-release data — provenance and optional HMM rebuild

The public release does **not** bundle the Pfam HMM (`Wheelhouse/hmm/scanner_pfam.hmm`); acquire it per `docs/EXTERNAL_ASSETS_GUIDE.md`. Pfam is
CC0, but it is **not bundled** here — you provision it yourself (see `docs/EXTERNAL_ASSETS_GUIDE.md`). This document is
kept only as **provenance** and a **rebuild recipe**: you do not need to fetch anything. Rebuild the
HMM from a newer Pfam-A only if you want to; the engine also runs without it (regex fallback).

## `Wheelhouse/hmm/scanner_pfam.hmm` (~4 MB) — curated Pfam HMM set

This is the 35 Pfam families the v0.3 scanner registry gates on, extracted from Pfam-A with each
family's curated gathering cutoff. The family list and accessions are in
`Wheelhouse/hmm/SCANNER_PFAM_MANIFEST.md`; the integrity SHA256 is recorded there.

Build it from Pfam-A (requires HMMER's `hmmfetch` / `hmmpress`):

```bash
# 1. Fetch Pfam-A (EBI) and index it
curl -O https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz
gunzip Pfam-A.hmm.gz
hmmfetch --index Pfam-A.hmm

# 2. Pull the 35 accessions listed in SCANNER_PFAM_MANIFEST.md into scanner_pfam.hmm
#    (accession list, one per line, e.g. PF00155.28 PF00202.28 ... PF04738.19)
grep -oE 'PF[0-9]{5}\.[0-9]+' Wheelhouse/hmm/SCANNER_PFAM_MANIFEST.md \
  | while read acc; do hmmfetch Pfam-A.hmm "$acc"; done > Wheelhouse/hmm/scanner_pfam.hmm

# 3. Press for pyhmmer/hmmscan and verify
hmmpress Wheelhouse/hmm/scanner_pfam.hmm
sha256sum Wheelhouse/hmm/scanner_pfam.hmm   # compare against the SHA in SCANNER_PFAM_MANIFEST.md
```

If you already run antiSMASH with `--fullhmmer`, its genome-wide Pfam output is an equivalent evidence
source and you can skip building this file (see `docs/troubleshooting/HMMER_DATA_WORKFLOW.md`).

## Provenance and rebuild rationale

The HMM is static reference data (Pfam models plus curated gathering cutoffs), not source. It is NOT bundled; it belongs in
operator-provisioned because it is large; it is not bundled here (see `docs/EXTERNAL_ASSETS_GUIDE.md`). The recipe above
exists only so you can regenerate the file from a newer Pfam-A release, verify its integrity against the
SHA in `SCANNER_PFAM_MANIFEST.md`, or rebuild it if it is ever lost. The teicoplanin MIBiG fixtures that
an earlier release stripped were retired in v9.7.270 in favour of the small public Micromonospora humida
fixture (`tests/fixtures/micromonospora_humida_JAFEUC01.zip`), which also ships in every tier — so there
is nothing to download to complete a checkout.
