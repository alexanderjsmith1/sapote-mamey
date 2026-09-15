# SHARED GUARD BLOCK — paste/inherit into every reuse prompt
*Vetted against Sapote–Mamey v9.7.7 contract · added 2026-06-10 after the TIGRFAM-extraction defect was found.*

These guards constrain evidence claims within the requested task. They do not override the
user's scope, permissions, output choices, or host instructions. Read `AGENTS.md` and
`docs/ASSISTANT_GOVERNANCE.md`; flag a conflict rather than expanding authority.

## G1 — Claim-safety (unchanged core)
- Compound identities are genome-mining predictions: "candidate", "predicted", "encodes apparent
  machinery for", "consistent with". Never "produces X"/"is X" without isolation/LC-MS data.
- KnownClusterBlast = source-derived similarity only; never name a product from KCB alone; state
  whether the similar-gene denominator is query-CDS count or reference-cluster-gene count.
- Internal annotations and external HMMER `domtblout` support sequence/domain hypotheses.
  An external HMM search does not by itself confirm a product, production, or bioactivity.
  Use source-bound per-locus evidence for class-level interpretation and preserve its limits.
- Never fabricate a citation. Preserve supplied citations as supplied/unverified unless a
  source or prior verification receipt supports them. Record verification source and date.
  Refresh when required and authorized; offline work may retain explicit unresolved citations.
  A search URL is a lookup aid, not a verified citation.
- Separate deterministic extraction from interpretation; no silent blanks — state missing evidence.

## G2 — Complete exact-locus identity mandate
Every individual BGC reference displays `strain / full node-or-contig / region / BGC alias`, in that
order, with all four components copied from one bound source record. This applies in every section and in
prose, tables, filenames, headings, and shortlists. If a component is unavailable or conflicting, stop
with an identity hold; do not guess, shorten the node/contig, or fall back to the alias. A node/region-only
validator is a useful supplemental check, not proof that the complete identity is present or correctly
bound.

## G3 — Evidence-JSON-first
Read `[StrainID]_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits` (per-locus HMM hits with
`tier1_diagnostic`) BEFORE any class call. Inventory/triage CSVs are summaries and do not carry the
per-locus domain list.

## G4 — TIGRFAM evidence availability
The June 2026 extraction-gap report is historical evidence, not a blanket claim about every run.
Check the bound engine version, JSON evidence mode, recorded extraction status and actual per-locus
hits. Current code includes diagnostic extraction and merge paths; that does not prove they ran or
covered every diagnostic in this package. If an expected channel is missing, mark it NOT_ASSESSED
or the applicable typed hold, inspect authorized raw-source evidence, and retain a recovery receipt.
Do not infer biological absence or silently rewrite the sealed package.

## G5 — Standing convention checks
Resolve hglE-KS prevalence and NAPAA exclusions from the selected current registry/profile.
Record cohort, rule version, and rationale; do not turn a historical cohort convention into a
universal biological conclusion. Preserve inventory visibility for excluded records;
 corrected BGC count = Interior + 0.5×Edge + 0.25×FC;
typed bioactivity metadata only; omission is `NOT_SUPPLIED` and assembly-aware weighting is an exploratory
Sapote heuristic, not a monolith rule.

## G6 — Misanchor warning (SM-P0-005 v9.7.123)
When authoring a Mode B card for a BGC whose triage board row (`_4_triage_board.csv`) has a
non-blank `Misanchor_Flag` column, insert this block at the start of §5 (Pharmacology):

```
> **⚠ KCB anchor note:** The KCB anchor compound carries a misanchor flag:
> `{Misanchor_Flag value}`. The anchor compound's committed class-diagnostic enzyme was
> not detected in this cluster's gene content. Cite the *class* the anchor belongs to —
> not the anchor name — as the basis for pharmacological comparison in §5.
```

Misanchor families: `aminoglycoside_anchor_no_DOIS` (no DOIS synthase); `polyene_anchor_<N_PKS_KS`
(too few KS domains); `enediyne_anchor_no_ene_KS` (TIGR03828 absent); `glycopeptide_anchor_no_oxyabc`
(no OxyA/B/C); `class_mismatch(...)` (anchor class incompatible with own products).
