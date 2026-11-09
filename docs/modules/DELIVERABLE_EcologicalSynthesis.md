# DELIVERABLE: Ecological Synthesis

**What this is.** A writing guide for a short ecological section on one strain. No tool produces it. You, or an assistant you direct, write it by hand from a validated package. Every statement is a labeled hypothesis. Nothing here is computed.

**Purpose.** Turn BGC-level evidence into testable ideas about how the strain's predicted chemistry could fit its host or habitat. Each idea cites specific BGC evidence, carries a confidence label, and names a test. A null result is a finding. Report it.

The [deliverable contract](../DELIVERABLE_CONTRACT.md) and the code win over this page. Claim-safety rules live in the contract. Terms such as BGC (biosynthetic gene cluster), TFBS (transcription factor binding site), KCB (KnownClusterBlast) and RG-GMCI are in the [glossary](../GLOSSARY.md).

## When to write it

Write it after the Mode B cards are done and the strain has host or habitat metadata. Mode B cards are the per-locus write-ups described in [MODE_B_WRITE.md](MODE_B_WRITE.md). A section with no per-hypothesis BGC citation, or one that leaves out a null result, is incomplete.

## Inputs

| Input | Used for |
|---|---|
| Deposited isolation source, from `manifest.json` | Context only. Report it as deposited. Isolation source is not ecological function. |
| TFBS hits across the BGCs | Regulatory coupling (step 1) |
| GH, LPMO, CotH and t2fas domains inside cluster boundaries | Polysaccharide gating (step 2) |
| `bldA` TTA tier | Developmental mapping (step 3) |
| Extract-level bioactivity and class calls | Matching to host defense (step 4) |
| HGT flags and the KCB top hit | Novel signals and the integrated model (steps 5 and 6) |

A missing input, an unrun scan or a failed parse is "not available". It is not a null result. A null result is a completed, source-bound check that found nothing, reported with its scope.

## Evidence ceilings

| Evidence basis | Strongest allowed wording |
|---|---|
| Direct assay | Activity under the recorded material and assay conditions. Fractionation alone does not give compound identity or BGC causation. |
| Bioinformatic BGC | "contains domains consistent with" or "predicted to encode" |
| Regulatory prediction | "predicts" or "consistent with regulated activation under" |
| Ecological analogy | "could represent" or "is hypothesized to" |
| Literature | Cited, with no strain-specific causality claimed |

## The eleven steps

1. **TFBS regulatory coupling table.** By working convention, a regulator seen in 2 or more BGCs is a coupled network and one seen in 6 or more is a genome-wide network. Read each in the host's context.
2. **Polysaccharide substrate coupling.** BGCs with GH or LPMO domains plus a matching TFBS are polysaccharide-gated candidates. State a null network explicitly.
3. **`bldA` tier to host development.** Map tiers T1 to T4 (the count of TTA codons in the scan: zero, 1-2, 3-5, 6 or more; see [Concepts Q&A](../GUIDE/06_Concepts_QandA.md#what-are-the-blda-tiers)) to the host's seasonal or developmental phases.
4. **Host disease-defense matching.** Match the strain's class capacity to the host's known pathogens. Capacity is not protection.
5. **Novel regulatory signals.** Regulators or contexts outside your standing set.
6. **Integrated model.** One falsifiable account that ties steps 1 to 5 to the host.
7. **BGC-by-BGC matrix.** One row per BGC: evidence, ecological role hypothesis, confidence.
8. **Ranking.** Rank hypotheses by how many evidence streams support them.
9. **Hypothesis format.** `[claim] based on [BGC, locus, domain, bitscore or TFBS], confidence [H/M/L], test: [experiment]`.
10. **Claim-safety pass.** Check every sentence against the ceilings above.
11. **Reviewer-attack block.** Append an ecological-overreach block. See [DELIVERABLE_ReviewerAttack.md](DELIVERABLE_ReviewerAttack.md), category 4.

The host-context tables (TFBS to ecology, `bldA` to phase, host to pathogen to class) are yours to fill. Use your own habitat categories and cite the source for each.

## Standing constraints

NAPAA is neutral in the rules registry: the engine neither downgrades it nor blocks it as a lead. By project rule it is left out of family (BiG-SCAPE) analyses and strain decks, so do not build family-level comparative claims on it. Whether NAPAA may carry other ecological comparisons is an open project decision: the registry rationale allows it, while some report builders still exclude it. Until it is decided, report NAPAA with its evidence and do not make it the basis of an ecological claim. The retired Nosema hypothesis stays retired. Where you do mention NAPAA, report it with its evidence like any other class.

Historical hglE-KS prevalence is context. It is not a habitat claim, so do not tie hglE-KS to a habitat. See the NAPAA and hglE-KS rows in the [glossary](../GLOSSARY.md).

## Output

A document you write by hand. Name it for your strain and keep it with the package it came from. Include the BGC-by-BGC matrix. To put it in the compiled report, run `python mamey_run.py write-narrative <package> --section ecological_synthesis --file <your.md>`.

## Checklist

- [ ] Every hypothesis cites a BGC locus as `strain / full contig / region / BGC alias`.
- [ ] Every hypothesis has a confidence label and a named test.
- [ ] Null results are stated.
- [ ] Every sentence respects the evidence ceilings.
- [ ] The reviewer-attack block is appended.
- [ ] Open holds are listed at the end.

## Template for one hypothesis

> Iron-economy hypothesis: `<strain> / <full contig> / region<NNN> / <BGC alias>` carries a siderophore-type locus, which could support competition for iron. Confidence M. Test: CAS assay under iron limitation. Bioinformatic evidence only.
