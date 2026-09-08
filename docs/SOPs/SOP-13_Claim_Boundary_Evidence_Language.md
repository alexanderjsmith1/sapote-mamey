# SOP-13 — Claim Boundary and Evidence Language

## Purpose

This SOP defines safe language for Sapote/Mamey reports.

Sapote/Mamey prioritizes BGCs and supports hypotheses. It does not identify compounds from sequence alone unless there is orthogonal evidence.

## Evidence levels

| Evidence | Supports | Does not support by itself |
|---|---|---|
| antiSMASH class | BGC class hypothesis | exact compound identity |
| KnownClusterBlast | similarity to known BGC | purified product claim |
| BLASTP hit | gene-function support | product identity |
| RG-GMCI | split/neighborhood support | chemical detection |
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
