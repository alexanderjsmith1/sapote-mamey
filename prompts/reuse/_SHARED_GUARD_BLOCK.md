# SHARED GUARD BLOCK — paste/inherit into every reuse prompt
*Vetted against Sapote–Mamey v9.7.7 contract · added 2026-06-10 after the TIGRFAM-extraction defect was found.*

These guards apply to ALL reuse prompts. They override any conflicting task instruction.

## G1 — Claim-safety (unchanged core)
- Compound identities are genome-mining predictions: "candidate", "predicted", "encodes apparent
  machinery for", "consistent with". Never "produces X"/"is X" without isolation/LC-MS data.
- KnownClusterBlast = source-derived similarity only; never name a product from KCB alone; state
  whether the similar-gene denominator is query-CDS count or reference-cluster-gene count.
- Marker calls (ene_KS vs hglE-KS, PepM, YcaO/TfuA, radical-SAM, Lan*) read from antiSMASH's INTERNAL
  annotations are disambiguation/screening targets, NOT confirmed products, unless external HMMER
  `domtblout` is supplied.
- Never fabricate a citation. No PMID/DOI/author/year/journal unless verified against PubMed/DOI.org
  this session; otherwise emit a PubMed *search* URL labeled `UNVERIFIED — lookup only`. A real-looking
  PMID is not a verified one.
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

## G4 — TIGRFAM-extraction guard ⚠ NEW (critical for class enumeration)
**Known defect (DEFECT_TIGRFAM_EXTRACTION_GAP_2026-06-10):** the package `gbk_pfam_hits` extraction is
Pfam-centric and drops ~99% of TIGRFAM diagnostic hits. Confirmed case: `AHBA_synth_RP` (rifamycin
diagnostic, 372 bits) was recorded only as generic `HAD_2` Pfam. **This causes false-negative class
calls for any TIGRFAM-diagnosed class**, including:
- **ansamycin / rifamycin** — AHBA_synth_RP
- **TOMM / thiopeptide / azole-RiPP** — TIGR03604
- **enediyne** (a polyketide subfamily) — ene_KS / TIGR03828
- **nucleoside** — NikJ-family / TIGR04186 and related

**Required behaviour:** when enumerating or ruling out any of the above classes, do NOT conclude absence
from the package alone. If the package shows only generic Pfam (e.g. HAD_2, generic aminotransferase)
at a locus that could be the diagnostic, OR if a strict-label search returns few/zero candidates for a
TIGRFAM-diagnosed class, **fall back to the raw genomic antiSMASH `antismash.detection.tigrfam` hits**
and report from there. Flag any such case `EVIDENCE_PENDING (TIGRFAM extraction gap)`. State explicitly
in the deliverable that strict counts for TIGRFAM-diagnosed classes are provisional until the extractor
fix lands.

## G5 — Standing convention checks
hglE-KS = PREV-001 (prevalent, flag as such, not novel); NAPAA is registry-neutral (listed, not
interpreted — not an automatic exclusion); corrected BGC count = Interior + 0.5×Edge + 0.25×FC;
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
