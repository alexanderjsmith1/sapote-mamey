# Historical known-BGC narrative corpus and calibration boundary

This is a **human narrative-review catalog**, assembled 2026-06-30, not a runnable calibration dataset or current source of scientifically accepted compound identities. Its 15-entry table contains explicit unconfirmed records. Preserve the original source record, declared reference versions, GBK/antiSMASH input hashes and citation decisions before an entry is used as an answer key. Public accession metadata alone does not establish redistribution/license scope or publication permission.

## Distinguish the three surfaces

1. This historical document lists selected comparator accessions and narratives. It does not contain hash-bound region inputs or a machine-readable baseline and is not consumed by `tools/calibration_run.py`.
2. Small CI/reference fixtures exercise specific software contracts. Passing their checks does not establish all biology or independent detector accuracy.
3. The current portable detector runner consumes `mamey/data/calibration_panel.json`, its hash-bound `calibration_baseline.json`, and a bound `reference_bgc_library.json`. The reference controls carry expected metadata and are explicitly **`NOT_EXERCISABLE`** without runnable, hash-bound antiSMASH regions (`tools/calibration_run.py:130–201,212–241`).

The runner's executed denominator is synthetic cases. Reference controls remain unexercisable and live targets unexecuted. `--live-input-root` checks region file containment/hashes only: `LIVE_INPUTS_HASH_VERIFIED` is not biological analysis or detector execution on live data. Preserve those denominators in any reported metrics. `PASS` is based on no baseline call flips; metrics/drops are recorded separately. CLI status0 does not turn metadata controls or hash-only targets into tested positives. Output JSON/TSVs are sequential direct writes without a complete code/output hash receipt (`:173–201,281–295`). Record the executed case/input scope with every calibration result.

Known-neighbor similarity is not identity of an unknown locus. The historical “same compound,” chemistry, pathway and public-domain assertions below require source-level confirmation before current adoption. Keep unresolved table entries held; do not count them as verified reference truth. For a locus under review, use strain / full node-or-contig / region / BGC alias; versioned reference accession remains a separate identity. A calibration narrative is not a finished current50 card: see [the current profile contract](MODEB_CURRENT50_V2_CONTRACT.md).

## Preserved historical record — not current instruction or accepted biology

The original catalog and recipe are retained verbatim for provenance. References to forthcoming batches, public-tier permissions and older card sections describe that historical session. They do not authorize new computation, disclosure or adaptation.

````text
# Calibration Corpus — Known-Compound Reference BGCs

*A catalog of well-characterized biosynthetic gene clusters with published structures, for spot-checking Mode B interpretive quality against ground truth. Use this corpus when training a new analysis chat, validating a class-call heuristic, or auditing whether claim-safe language and KCB-scoring intuition have drifted.*

*Distinct from `docs/CI_REFERENCE_FIXTURES_GUIDE.md`, which covers small antiSMASH-signature fixtures wired into automated pytest concordance checks. This document is for human-facing Mode B calibration — narrative interpretation quality, not automated test coverage.*

---

## Purpose

Every BGC in this corpus has a published compound identity and (for most) a characterized biosynthetic pathway in the literature. When training or recalibrating Mode B interpretation:

1. Run the antiSMASH output through gene-by-gene reading exactly as you would for an unknown strain BGC.
2. Write the interpretive argument — what the genes mean together, not just a domain inventory.
3. Compare the read against the published structure and pathway.
4. Note where the read matches, where it's plausible-but-unconfirmed, and where it would have been wrong without literature access.

This is the same discipline as a real Mode B card, except the answer key exists. A reference card (see `BGC003_ModeB_narrative_draft.md` for the target register) typically runs §1–§8 in full narrative form, then closes with a **Calibration note** comparing the read against the literature — this section does not appear in real Mode B cards since there is no answer key for an unpublished strain.

---

## Corpus inventory

All entries below are public MIBiG reference clusters or named-compound GenBank entries — safe for any tier, no PRIVATE tagging required.

| ID / Accession | Compound | Organism | Class | Core genes (antiSMASH) | Products called |
|---|---|---|---|---|---|
| BGC0000002 | aculeximycin (unconfirmed — verify via region GBK) | *Kutzneria albida* DSM 43870 | T1PKS / oligosaccharide | 15 | T1PKS, oligosaccharide |
| BGC0000240 | lomaiviticin A | *Salinispora pacifica* | T2PKS (diazo-fluorene dimer) | 2 | T2PKS |
| BGC0000243 | macrotetrolide (nonactin) | *Streptomyces griseus* subsp. *griseus* | polyketide (unusual — non-canonical PKS) | 0 | unknown |
| BGC0000245 | medermycin | *Streptomyces* sp. AM-7161 | T2PKS (angucycline-adjacent) | 2 | T2PKS |
| BGC0000247 | mithramycin | *Streptomyces argillaceus* | T2PKS / oligosaccharide (aureolic acid family) | 6 | T2PKS, oligosaccharide |
| BGC0000249 | nogalamycin | *Streptomyces nogalater* | anthracycline-type (T2PKS family, unscored core) | 0 | unknown |
| BGC0000263 | ravidomycin | *Streptomyces ravidus* | T2PKS (benzo[a]naphthacenequinone) | 2 | T2PKS |
| BGC0000264 | resistomycin | *Streptomyces resistomycificus* | T2PKS (pentangular polyphenol) | 2 | T2PKS |
| BGC0001773 | (plasmid-borne — verify region via gbk) | *Pseudonocardia* sp. HH130630-07 | T1PKS | 6 | T1PKS |
| BGC0002573 | phosphoramidon | *Streptomyces mozunensis* MK-23 | peptidyl nucleotide / minimal cluster | 1 | other |
| JN674503.1 | polyoxin (genomic context A) | — | nucleoside antibiotic | 2 | nucleoside |
| EU158805.1 | polyoxin (genomic context B) | — | nucleoside antibiotic | 2 | nucleoside |
| OR785474.1 | bafilomycin | — | T1PKS / saccharide (16-membered macrolide) | 6 | T1PKS, saccharide |
| KP410250.1 | trioxacarcin A | — | PKS-like / T2PKS / betalactone / oligosaccharide hybrid | 11 | PKS-like, T2PKS, betalactone, oligosaccharide, saccharide |
| MT361594.1 | venturicidin | — | T1PKS / NRPS / saccharide hybrid | 10 | NRPS, T1PKS, saccharide |

**Two entries need region-level confirmation before use:** BGC0000002 is a complete-genome GenBank entry (*K. albida*) — the antiSMASH DEFINITION line reflects the whole genome, not the BGC name; pull the compound identity from the region GBK or the MIBiG page directly before treating "aculeximycin" as confirmed. BGC0001773 is a plasmid entry without a compound name in the DEFINITION line — same caveat.

**Thematic clusters for comparative training:**
- **Type II aromatic polyketides (angucycline/anthracycline family):** BGC0000240 (lomaiviticin), BGC0000245 (medermycin), BGC0000247 (mithramycin), BGC0000249 (nogalamycin), BGC0000263 (ravidomycin), BGC0000264 (resistomycin) — six clusters sharing the minimal PKS (KSα/KSβ/ACP) core logic with divergent tailoring. Strong set for practicing the "shared core, divergent tailoring" interpretive pattern that recurs constantly in real strain analysis.
- **Hybrid PKS/NRPS macrolides:** venturicidin, bafilomycin — both 16-membered macrolide-adjacent with saccharide decoration; venturicidin adds an NRPS module.
- **Nucleoside antibiotics:** the two polyoxin accessions — useful pair for practicing cross-accession KCB consistency (same compound class, different genomic context, do the core genes agree).
- **Minimal/atypical clusters:** BGC0000243 (0 antiSMASH-scored core genes despite being a real, published pathway — macrotetrolide biosynthesis uses an unusual non-canonical assembly logic that antiSMASH's standard PKS rules don't fully capture), BGC0002573 (5 total genes, 1 core — phosphoramidon's biosynthesis is genuinely minimal). Both are good tests of "low antiSMASH core-gene count does not mean low biosynthetic sophistication" — the opposite of the usual heuristic.

---

## How to use this corpus

**For training a new analysis chat:** pick 2–3 entries from different thematic clusters, run gene-by-gene reads, and check the resulting interpretation against the published pathway (search the compound name + "biosynthesis" + "gene cluster"). Confirm the chat correctly used claim-safe language even when working from a known compound — the discipline should not relax just because the answer is public.

**For auditing class-call heuristics:** the six type II polyketide entries are a strong test of whether a scoring rule correctly identifies the shared core across divergent tailoring patterns. If a heuristic flags lomaiviticin's minimal PKS core differently from resistomycin's, that is worth investigating — they should score structurally similar at the core, divergent at the tailoring layer.

**For testing low-core-gene edge cases:** BGC0000243 and BGC0002573 deliberately probe the assumption that few antiSMASH-flagged core genes implies a simple or low-priority pathway. Both are published, real pathways with unusual biosynthetic logic that the standard PKS/NRPS rule set under-recognizes. Any heuristic that auto-downgrades low-core-gene-count BGCs should be checked against these two.

**For comparative consistency:** the two polyoxin accessions (JN674503.1, EU158805.1) are the same compound from different genomic submissions. A correctly-calibrated KCB read should treat them as the same class with consistent core-gene logic, even though they come from different antiSMASH runs.

---

## Source

Corpus assembled 2026-06-30 from two batches of antiSMASH output: a MIBiG reference set (BGC0000002–BGC0002573, 10 entries) and a named-compound GenBank set (polyoxin ×2, venturicidin, trioxacarcin A, bafilomycin, 5 entries). Four further batches are expected in subsequent sessions — append new entries to the inventory table above rather than creating parallel documents.

All entries are public domain / MIBiG-curated. None require PRIVATE tagging. Safe for inclusion in any tier including SID-public.

````
