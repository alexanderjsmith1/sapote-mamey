# Patch Chat Handoff — Wise Fragmented PKS Workflow

## Current entry: patch history versus actual queue behavior

This body records a historical patch request and example batch counts. It is not a present user instruction,
external submission authorization or proof of current execution. Current queue route is
`python mamey_run.py wise-fragmented-pks --input-fasta <existing-ranked-fasta> --outdir <candidate-queue>`;
`mamey/cli.py:8055–8064` supplies target 85000, hard cap 100000 and two active files by default.
These are shipped software defaults; check current service limits separately before an authorized submission.
The command consumes an already ranked FASTA; it does not itself discover/rank all proteins or run BLASTP.
Use `--target-residues 50000` for the conservative target, not an invented CLI `--extra-safe` flag.

Actual `mamey/wise_fragmented_pks.py:83–109` sorts ranks and packs by residue target, but retains a single
oversized sequence with a warning. The writer (`:136–150`) can emit that active batch as ready_to_run while
under_100k is false. Consequently the historical universal “no file exceeds 100000” criterion is not
implemented for these singleton exceptions. Inspect residue_count, under_100k and per-record warnings;
ready_to_run alone is not safe-submission proof. An oversized single sequence remains an explicit hold
requiring a separately chosen authorized route and its own execution receipt.

Queue files, ledgers, summary and README use deterministic destinations and can replace earlier outputs.
Use one bound candidate and source path/SHA-256 receipts; do not copy the package/evidence corpus.
Pending/deferred queue states do not prove submission, completion or admitted biological evidence.

<!-- Historical source text follows. -->

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
