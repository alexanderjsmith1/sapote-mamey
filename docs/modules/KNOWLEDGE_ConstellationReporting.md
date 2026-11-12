# KNOWLEDGE — Constellation Reporting Fidelity

This page is a reporting rule for people who write summaries, cards and front pages. When several genes together
form one diagnostic set (a *constellation*), report every member. Do not shrink the set to its single
highest-scoring gene. The claim-safety checks look for overclaims, so they do not catch this kind of
under-report. No code applies this rule; [the deliverable contract](../DELIVERABLE_CONTRACT.md) and the code win
over this page. Related pages: [contig-rescue reconstruction](DELIVERABLE_ContigRescueReconstruction.md),
[LMPKS rescue](DELIVERABLE_LMPKSRescue.md) and [judgment checks](KNOWLEDGE_JudgmentChecks.md). The cassette story
below is a historical reporting example with incomplete identity.

## 1. The failure this prevents

A historical report described a candidate gene set omitted from a summary. Its source records and complete locus identities are not bound here, so detection, functional assignments and the proposed relationship remain unverified. Preserve each source-bound member and alternatives during review. A highest-scoring-gene summary can omit relevant evidence; assess that risk without assuming the historical detection or pathway interpretation was correct.

## 2. Why it is dangerous in fragmented genomes

Fragmentation can distribute relevant observations across records. A top-hit-only summary can hide those observations and their gaps; preserve the admitted record scope without assuming they constitute a single pathway.

## 3. The rule (with teeth)

**R1 — Candidate set, every relevant member.** Report neighboring genes that share a reference-family hit as a candidate set. List each full locus and gene identity, annotation, underlying reference match, coverage, uncertainty and alternative explanations. Similarity and proximity do not alone prove a functional cassette, linkage across contigs or one pathway. Preserve the relevant members together rather than collapsing them to one representative; use functional cassette or split-pathway labels only to the degree supported by reviewed evidence.

**R2 — Contig-flank census.** A boundary walk must state honestly what it *cannot* see —
the un-annotated ORFs past a cluster's edge — rather than implying there is nothing there.
Delivered by `build_reconstruction.py` §4: every CDS in each fragment's selected region GenBank
file, flagged `★ scaffold` / `· CB-family` / `unexplained`. The region file covers the antiSMASH
region and its flanks, not necessarily the whole contig. This census is limited to annotated CDS parsed from the selected region file; unannotated ORFs and sequence outside that file are not assessed.

**R3 — Collective weight beats individual score.** This is a reporting rule. No ranking code treats a
constellation as a unit, so the engine's scores still rank genes and regions one by one. When you write up a
cassette whose members each score below a lead threshold but which together are consistent with one pathway,
report the set and its collective evidence beside the ranked output. Do not drop it because of the individual
scores.

## 4. How to verify a report passes

- Does every split-pathway arm list all its genes, or just the loudest one?
- Is each deoxysugar/NRPS/PKS cassette named and fully enumerated?
- Does the boundary walk say what it cannot see, or imply completeness?
- Would the report survive the bench question *"weren't there more genes there?"* — a useful completeness question; the historical event remains unverified here?

