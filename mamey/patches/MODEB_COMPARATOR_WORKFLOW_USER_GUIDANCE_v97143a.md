# Sapote–Mamey Mode B Workflow Patch Master Packet

## Purpose

This packet converts what we learned during the AS-XXX NODE_58 / NODE_107 / NODE_24 / NODE_30 workup into implementation-ready Sapote–Mamey patches.

The core lesson:

> Mode B must become an interactive evidence-escalation workflow, not a static BLASTP table generator.

When Sapote–Mamey detects large modular proteins, repeated comparator hits, possible split/composite loci, missing pathway parts, or different comparator axes, it must guide the user toward the next decisive evidence step: comparator antiSMASH, synteny scoring, HMMER/domain architecture, missing-parts accounting, and claim-safety updates.

## Highest-priority patch order

| Priority | Patch | Status | Why |
|---:|---|---|---|
| 1 | Mandatory AA-Length Schema Gate | ready | Prevents wrong calls from missing protein sizes |
| 2 | Large-Protein Misannotation Guard | ready | Prevents huge SDR/oxidoreductase modules being misread as small enzymes |
| 3 | Mode B Coverage Contract | ready | Prevents false “full contig” claims |
| 4 | Mode B Comparator Workflow Gate | ready | Prompts user to run/upload comparator antiSMASH |
| 5 | Split/Composite BGC Claim-Safety Classifier | ready | Prevents forced merges and overclaims |
| 6 | Comparator Synteny Scoring Patch | spec-ready | Handles uploaded comparator antiSMASH |
| 7 | antiSMASH Region Import Patch for External Comparators | spec-ready | Parses comparator regions and accessions |
| 8 | Missing Parts Ledger | spec-ready | Makes fragmented BGCs interpretable |
| 9 | Domain-Architecture Required-Next-Step Patch | spec-ready | Routes large PKS/NRPS proteins to HMMER |
| 10 | Do Not Collapse Comparator Axes | ready | Keeps unrelated comparator stories separate |
| 11 | Mode B Evidence Ledger | spec-ready | Separates evidence from interpretation |
| 12 | User-Action Queue Patch | ready | Tells user what to do next |
| 13 | Locus Map Quality Gate Patch | spec-ready | Prevents overconfident figures |
| 14 | Mode B Patch-Chat Export Bundle | ready | Creates deterministic handoff ZIPs |
| 15 | Quiet-Time Heartbeat for Long Workups | ready | Keeps long runs transparent |

## AS-XXX regression story

### Hypothesis 1: NODE_58 + NODE_107

Primary antifungal-direction modular PKS / hybrid NRPS-PKS hypothesis.

- NODE_58 = primary modular T1PKS/polyene-macrolide-like core.
- NODE_107 = best companion/parallel NRPS/T1PKS locus.
- Not proven a single split pathway.
- Comparator axis: *Streptomyces cinnamoneus* / LX-29 / *Streptomyces violaceusniger* T1PKS regions 019/042/030.

### Hypothesis 2: NODE_24 + NODE_30

Candidate NPDC041969-like PKS-context composite.

- NODE_24 = core-like transAT/PUFA/PKS biosynthetic segment.
- NODE_30 = accessory/export/regulatory/release/tailoring segment.
- Supported by repeated top BLASTP hits to *Streptomyces* sp. NPDC041969.
- Requires comparator antiSMASH/synteny check before stronger claim.
- Candidate linkage only, not confirmed contiguous.

## Core acceptance test

The patched system passes when it would have automatically told the user:

1. “NODE_24 + NODE_30 repeatedly map to *Streptomyces* sp. NPDC041969. Run/upload NPDC041969 antiSMASH next.”
2. “AA lengths are mandatory in the same Mode B table as BLASTP/function evidence.”
3. “ctg24_2 and ctg30_19 are huge SDR-labelled proteins; do not interpret as standalone SDR enzymes.”
4. “NODE_58 is a separate comparator axis and must not be collapsed into the NPDC041969 model.”
5. “This is candidate linkage, not a confirmed split BGC.”
