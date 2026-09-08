# PIPELINE DEFECT — TIGRFAM diagnostics dropped in evidence extraction
**Logged:** 2026-06-10 · **Severity:** HIGH (affects class calls for TIGRFAM-diagnosed pathways)
**Found via:** rifamycin recovery test on *A. rifamycini* DSM 43936 (validation benchmarking).

## Symptom
The Mamey package's `[StrainID]_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits` under-captures
TIGRFAM-family domain hits relative to the source antiSMASH output. For *A. rifamycini*:
- Genomic antiSMASH output: **293 TIGRFAM hits (251 ≥100 bits)**.
- Package extracted evidence: **4 TIGRFAM-named entries out of 544 total** (~99% drop).

## Concrete consequence (the diagnostic case)
Locus `ctg23_9` carries, in the genomic antiSMASH JSON, the diagnostic
`AHBA_synth_RP` (AHBA-synthesis-associated protein; TIGRFAM; score 372; E 1.4e-112) — AHBA synthase is
the defining ansamycin/rifamycin precursor enzyme. In the sealed package the SAME locus is recorded
only as `HAD_2` (generic Pfam haloacid dehalogenase, 101.7 bits, `tier1_diagnostic: false`). The
extraction kept the weaker Pfam annotation and dropped the strong TIGRFAM diagnostic for the same gene.
Net effect: the single most important gene for calling rifamycin was flattened to "generic
dehalogenase," and the rifamycin recovery test failed at the package layer despite the genome
containing the diagnostic.

## Scope / impact
Affects any compound class whose diagnostic is a TIGRFAM model rather than Pfam, e.g.:
- AHBA_synth_RP — ansamycins/rifamycins
- TIGR03604 — TOMM/thiopeptides (already known to the B2 work as the one HMM-only CCTT marker)
- TIGR03828 (ene_KS) — enediynes; TIGR04186 (NikJ) — nucleosides; etc.
This is the SAME failure family as the evidence-JSON and ranthipeptide issues fixed this session:
real diagnostic evidence present in the antiSMASH source, not surfaced downstream. Here the loss is at
the Mamey extraction step (which builds `gbk_pfam_hits`), not the Sapote judgment step.

## Fix (Mamey-side, code)
The GBK/JSON evidence extractor must capture TIGRFAM hits alongside Pfam, and when a locus has multiple
domain annotations, retain the strongest diagnostic (and/or keep all, with source DB recorded) rather
than collapsing to a single Pfam call. Tier-1 flagging must consider TIGRFAM diagnostics
(AHBA_synth_RP, TIGR03604, etc.). Add a regression check: for a known TIGRFAM-diagnosed strain, the
diagnostic must appear in `gbk_pfam_hits` with its TIGRFAM identity and bitscore.

## Interim Sapote-side guard (until the extractor is fixed)
When a strain is a candidate for a TIGRFAM-diagnosed class (ansamycin, TOMM/thiopeptide, enediyne,
nucleoside) and the package shows only generic Pfam annotations at the expected locus, do NOT conclude
absence — flag `EVIDENCE_PENDING (TIGRFAM extraction gap)` and check the raw genomic antiSMASH
`antismash.detection.tigrfam` hits directly. This mirrors the evidence-JSON-first rule but extends it
to the genomic source when the package extraction is suspect.

## Status
**FIXED + VERIFIED (2026-06-10, v9.4.1-tigrfix).** Implemented in `mamey/antismash_evidence.py`:
new `extract_tigrfam_hits()` reads the JSON `antismash.detection.tigrfam` module for the diagnostic
accessions in `DIAGNOSTIC_TIGRFAM` (TIGR01454 AHBA/ansamycin, TIGR03604 thiopeptide, TIGR03828 ene_KS/
enediyne, TIGR04186 NikJ/nucleoside); `merge_tigrfam_into_pfam_hits()` appends them into
`gbk_pfam_hits` (append-only — both the generic Pfam and the TIGRFAM diagnostic are retained); the four
TIGR accessions added to `_TIER1_DOMAIN_NAMES`. Wired into `mamey/cli.py` at the extraction call site.
**Verified on the real rifamycini genome:** AHBA_synth_RP (TIGR01454) now surfaces on ctg23_9 at
score 372.3, tier1=True (previously only generic HAD_2); ene_KS (TIGR03828) also recovered on ctg3_346
at 306.7. Regression test `tests/test_tigrfam_extraction.py` (3/3 pass). Note: only the targeted
diagnostics are surfaced (not the full ~293-hit TIGRFAM set) to keep extraction focused on
class-defining markers; broaden `DIAGNOSTIC_TIGRFAM` if other TIGRFAM-diagnosed classes are needed.

## Historical (pre-fix) record
