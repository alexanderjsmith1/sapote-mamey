# HMMER Data Workflow

> **Release 1 limitation:** `mamey_markers.hmm` is not included in this release. The HMM profile library is a Release 2 deliverable. The command below is provided for reference; substitute your own HMM database or use antiSMASH `--fullhmmer` output (which runs Pfam genome-wide) as an equivalent. Until `mamey_markers.hmm` is available, HMMER-dependent cells receive `NEEDS_HMMER_DOMTBLOUT` status.

HMMER is the standalone path for profile/domain/cassette evidence. It is not a replacement for BLASTP; it answers a different question: what conserved domain or marker profile is present?

## Required input

- protein FASTA (`.faa`) derived from antiSMASH GenBank files or a local gene caller/annotation workflow;
- Mamey marker HMM library, or a user-provided HMM database;
- `hmmscan --domtblout` output.

## Recommended command

```bash
hmmscan \
  --cpu 8 \
  --domtblout STRAIN_hmmscan.domtblout \
  mamey_markers.hmm \
  STRAIN_proteins.faa \
  > STRAIN_hmmscan.txt
```

Mamey should parse `domtblout` for workbook evidence and avoid storing huge verbose text when structured tables are enough.

## Cells this fills

- marker hits;
- cassette/domain evidence;
- enzyme-family calls;
- RiPP/tailoring/resistance/transporter evidence where HMM profiles are available;
- confidence flags based on e-value, bitscore, and coverage thresholds.
