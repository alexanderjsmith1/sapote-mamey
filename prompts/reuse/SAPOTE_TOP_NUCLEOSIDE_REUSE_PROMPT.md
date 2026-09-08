# REUSE PROMPT — Top Nucleoside BGCs (claim-safe)
*Vetted against Sapote–Mamey v9.7.7 contract · `prompts/reuse/` · inherits `_SHARED_GUARD_BLOCK.md` (G1–G5).
Use after a cumulative master workbook + per-strain outputs exist.*

> ⚠ **THIS CLASS IS DIRECTLY AFFECTED BY THE TIGRFAM-EXTRACTION DEFECT (G4).** Nucleoside diagnostics
> (NikJ-family / TIGR04186 and related) are TIGRFAM models. The package extraction drops ~99% of
> TIGRFAM hits, so a strict-label search on the package alone WILL under-report nucleoside candidates —
> the same way the rifamycin AHBA diagnostic was lost. **You must apply the G4 genomic-tigrfam
> fallback for this prompt; a low strict count from the package is NOT evidence of absence.**

## Task
1. Search all BGC records for strict `nucleoside` product labels and KCB text.
2. **Apply G4:** also read the raw genomic antiSMASH `antismash.detection.tigrfam` hits for
   nucleoside-diagnostic models; reconcile against the package. Any locus showing only generic Pfam in
   the package but a nucleoside TIGRFAM in the genomic output is a recovered candidate — flag
   `EVIDENCE_PENDING (TIGRFAM extraction gap)`.
3. Rank strict nucleoside candidates by Sapote review priority.
4. If <20 strict candidates exist (likely, given G4), make a strict section AND an explicitly separate
   nucleoside-adjacent lookup-target section with cautious evidence tiers. **State that strict counts
   are provisional pending the extractor fix.**
5. Per row: strain · `BGC_ID (contig · regionXXX)` · products · boundary · architecture · assembly tier ·
   genus · host · AB/AF/novelty · Sapote lane · KCB score + top hit · closest candidate product ·
   similarity count + denominator · MIBiG URL · PubMed lookup URL · marker triggers · TIGRFAM-source
   note (package vs genomic) · claim-safe why-interesting paragraph.
6. Outputs: CSV · XLSX · HTML · Markdown · no-overlap PDF · final ZIP.

## Required language
candidate nucleoside BGC · source-derived label · KCB similarity only · consistent with · requires
domain-level + metabolomic confirmation. Avoid produces/confirmed; no unverified PMID/DOI.
