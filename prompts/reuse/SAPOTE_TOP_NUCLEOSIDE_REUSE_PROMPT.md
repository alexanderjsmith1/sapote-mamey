# REUSE PROMPT — Top Nucleoside BGCs (claim-safe)

> **Reuse status:** the v9.7.7 vetting label is historical. Bind the selected current contract, source version and actual package evidence before reuse. Apply the current shared guards; this template does not authorize extra scans, package mutation, external messaging or publication.
*Vetted against Sapote–Mamey v9.7.7 contract · `prompts/reuse/` · inherits `_SHARED_GUARD_BLOCK.md` (all applicable guards).
Use after a cumulative master workbook + per-strain outputs exist.*

> **G4 applies to this class.** Nucleoside diagnostics (NikJ-family TIGR04186 and related models) are TIGRFAM hits. They live only in the antiSMASH JSON, not in the region GBKs. The package surfaces a short allowlist of diagnostic TIGRFAM accessions; related nucleoside models outside that list never reach it. The record pass that reads them can also fail; its outcome is in the `record_extraction` receipt. A package-only strict count is therefore a lower bound, not evidence of absence. Do not quote the old "~99% dropped" figure; it described an earlier extractor.

## Task
1. Search all BGC records for strict `nucleoside` product labels and KCB text.
2. **Apply G4 (required):** read the raw genomic antiSMASH `antismash.detection.tigrfam` hits for nucleoside-diagnostic models and reconcile them with the package. Check the `record_extraction` receipt for failed or skipped files. A locus that shows only generic Pfam in the package but a nucleoside TIGRFAM hit in the genomic output is a recovered candidate; flag it `EVIDENCE_PENDING (TIGRFAM extraction gap)`. Keep the raw-source observation beside the package; never edit sealed evidence.
3. Rank strict nucleoside candidates by Sapote review priority.
4. If <20 strict candidates exist, make a strict section AND an explicitly separate
   nucleoside-adjacent lookup-target section with cautious evidence tiers. **State that strict counts
   are a lower bound and name any locus still held after the G4 review.**
5. Per row: strain · `strain / full node-or-contig / region / BGC alias` · products · boundary · architecture · assembly tier ·
   genus · host · AB/AF/novelty · Sapote lane · KCB score + top hit · closest candidate product ·
   similarity count + denominator · MIBiG URL · PubMed lookup URL · marker triggers · TIGRFAM-source
   note (package vs genomic) · claim-safe why-interesting paragraph.
6. Outputs: CSV · XLSX · HTML · Markdown · no-overlap PDF · final ZIP.

## Required language
candidate nucleoside BGC · source-derived label · KCB similarity only · consistent with · requires
domain-level + metabolomic confirmation. Avoid produces/confirmed; no unverified PMID/DOI.
