# SOP-13 — Claim Boundary and Evidence Language

## Purpose

This SOP defines safe language for Sapote/Mamey reports.

Sapote/Mamey prioritizes BGCs and supports hypotheses. It does not identify compounds from sequence alone unless there is orthogonal evidence.

## Evidence levels

| Evidence | Supports | Does not support by itself |
|---|---|---|
| antiSMASH class | BGC class hypothesis | exact compound identity |
| KnownClusterBlast | similarity to known BGC | purified product claim |
| BLASTP hit | sequence homology / qualified function hypothesis | demonstrated function or product identity |
| RG-GMCI | candidate split/linkage from shared reference geometry | physical contig linkage or chemical detection |
| resistance/transporters | ecological or self-protection context | activity claim |
| literature | plausibility / precedent | activity in this strain |
| LC-MS/MS | metabolite evidence | gene function unless linked |
| purified compound | compound identity/activity | genome-wide mechanism |

## Acceptable language

Use:

- "supports a BGC class call"
- "resembles a known biosynthetic neighborhood"
- "contains homologs of..."
- "is a priority for follow-up"
- "candidate antimicrobial lead"
- "claim-safe evidence suggests..."

## Prohibited language without orthogonal evidence

Avoid:

- "produces compound X"
- "is compound X"
- "confirmed antifungal"
- "confirmed antibacterial"
- "this BGC makes..."
- "definitive product identity"

## BLASTP-specific boundary

BLASTP may support:

- gene function,
- protein family,
- conserved pathway components,
- related-genome selection,
- BGC class confidence.

BLASTP alone may not support:

- final metabolite identity,
- bioactivity,
- purified compound presence,
- exact biosynthetic product.

## Bug-hunt checks

1. Reports should not say "produces" unless evidence supports production.
2. BLASTP follow-up should not call compound identity.
3. KCB should not be treated as product confirmation.
4. Public tier should avoid private strain claims.
5. Known controls should be described as controls/reference sequences.

## Preserve the evidence state and its subject

Every individual locus needs strain / full contig / region / BGC alias copied from one bound source. Sequence similarity, an annotation title, a template and a structural pass establish different things. Report observations, inference, alternatives and unresolved provenance separately. Do not let an appealing class name stand in for the underlying query, reference and denominator.

For RG-GMCI, the implementation's claim ceiling is candidate linkage, not proof of physical linkage or product identity (`mamey/rggmci.py:1491`). For BLASTp, missing rows in an observed-hit summary are not tested negatives (`mamey/blastp_followup.py:459–497`). Qualify conclusions by admitted input/result scope; unsubmitted, unbound, skipped and completed no-hit states cannot be interchanged.

A mechanical deliverable-suite pass validates reported manifest text and count fields, not artifact existence, citation accuracy or biological conclusions (`tools/check_deliverable_suite.py:25–79`). A `PASS` validator result likewise has scoped gates and may retain unevaluated provenance (`mamey/validate.py:1003–1045`). Final scientific/adoption authority remains with the project owner. See [the deliverable contract](../DELIVERABLE_CONTRACT.md) and [the shared claim guards](../../prompts/reuse/_SHARED_GUARD_BLOCK.md).
