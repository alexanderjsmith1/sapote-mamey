# KNOWLEDGE — Constellation Reporting Fidelity

> **Filing.** `docs/modules/KNOWLEDGE_ConstellationReporting.md`.
> **References:** `DELIVERABLE_ContigRescueReconstruction.md`, `DELIVERABLE_LMPKSRescue.md`, `KNOWLEDGE_JudgmentChecks.md`, `DELIVERABLE_CONTRACT.md`.
> **Precedence.** `DELIVERABLE_CONTRACT.md` wins; the active monolith wins.
> **Status:** `KNOWLEDGE` (a reporting guard; the per-gene extraction lives in Mamey).
> **One-line purpose.** Stop the summarization layer from compressing a multi-gene diagnostic *constellation* down to its single highest-scoring member — the under-report failure mode the claim-safety machinery does not catch.

## 1. The failure this prevents (AS-XXX NODE_105, 2026-06-02)

A real, correctly *detected* three-gene NDP-deoxysugar cassette (`ctg105_14/15/16`) sitting
beside the halogenase (`ctg105_17`) was compressed in a compiled chapter to one line —
`Trp halogenase (567.6, separate contig)`. The three sugar genes — the **entire
glycosylation half** of the split-pathway argument — were silently dropped. Nothing errored;
antiSMASH detected them; the earlier analysis had them right. The summary rule "keep the
highest-scoring gene in each region" deleted them because the halogenase out-scored each
sugar gene *individually* — but the cassette's value is **collective**.

This is **not** a detection failure and **not** an overclaim. It is the opposite: an
*under-report* that omitted real supporting evidence and weakened a legitimate, claim-safe
hypothesis. The existing don't-overclaim guards are blind to it.

## 2. Why it is dangerous in fragmented genomes

The more shattered the assembly, the more the real signal lives in **scattered
constellations** rather than tidy complete clusters — so a "keep the top hit" rule discards
exactly the evidence a fragmented genome encodes its best leads in.

## 3. The rule (with teeth)

**R1 — Named constellation, every member.** When two or more genes that are *contiguous on a
contig* share a **top-hit reference cluster family**, report them as a **named
constellation**, listing every member with its locus tag, function, and per-gene reference
identity. They **may not be collapsed** to a single representative gene in any summary-level
output — priority table, candidate card, Mode B header, or front page.

Constellations include (non-exhaustive): **deoxysugar cassettes**, **split-pathway arms**,
**NRPS module sets**, **PKS module sets**, **RiPP precursor + maturation pairs**.

**R2 — Contig-flank census.** A boundary walk must state honestly what it *cannot* see —
the un-annotated ORFs past a cluster's edge — rather than implying there is nothing there.
Delivered by `build_reconstruction.py` §4 (every flank CDS flagged
`★ scaffold` / `· CB-family` / `unexplained`).

**R3 — Collective weight beats individual score.** Ranking and selection operate on the
constellation as a unit. A cassette whose members each score below a lead threshold but which
*together* complete a pathway is promoted on the collective evidence, not dropped on the
individual scores.

## 4. How to verify a report passes

- Does every split-pathway arm list all its genes, or just the loudest one?
- Is each deoxysugar/NRPS/PKS cassette named and fully enumerated?
- Does the boundary walk say what it cannot see, or imply completeness?
- Would the report survive the bench question *"weren't there more genes there?"* — the exact
  question that caught the original failure?

*Companion narrative: "When the Evidence Survived but the Report Didn't" (AS-XXX NODE_105).*
