# Patch Chat Handoff — Wise Fragmented PKS Workflow

## The issue

The workflow should not act untrained. It should understand the practical shape of the user's discovery process.

The user is doing fragmented-polyketide discovery across many strains. The right first step is not whole-assembly phmmer and not six blind FASTA batches. The right first step is a small, ranked, residue-safe FASTA panel that can actually be pasted into NCBI BLASTP.

## What happened

An all-strain TOP30 FASTA had 30 proteins but 128,778 residues. NCBI rejected it because the web limit is 100,000 residues.

A naive split made:
- Part 1: ranks 1–22, 83,563 residues
- Part 2: ranks 23–30, 45,215 residues

The user correctly pointed out that Part 2 should continue filling with ranks 31+ until it is also near 80–85 kb.

Corrected split:
- Batch 1: ranks 1–22, 83,563 residues
- Batch 2: ranks 23–41, 82,618 residues
- Batch 3: ranks 42–64, 77,881 residues

## Patch behavior

Make Sapote–Mamey do this automatically:

1. Rank candidate PKS/NRPS/polyene/transAT proteins.
2. Export NCBI-safe FASTA batches using residue totals.
3. Target ~85,000 residues, hard cap 100,000.
4. Provide extra-safe 50,000 residue batches.
5. Tell the user to run Batch A first.
6. Wait for BLASTP/HMMER results before broad prospecting.
7. Use results to guide missing-gene/comparator searches.

## Acceptance criteria

- No NCBI web FASTA exceeds 100,000 residues.
- Batch 2 continues past rank 30 if there is room.
- User receives a copy/paste-ready file.
- README tells the user which file to run first.
- Manifest includes protein lengths and batch residue totals.
- Output avoids overconfident product claims.
