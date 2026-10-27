# REUSE PROMPT — Top Halogenation-Containing BGC Leads (claim-safe)

> **Reuse status:** the v9.7.7 vetting label is historical. Bind the selected current contract, source version and actual package evidence before reuse. Apply the current shared guards; this template does not authorize extra scans, package mutation, external messaging or publication.
*Vetted against Sapote–Mamey v9.7.7 contract (DELIVERABLE_CONTRACT + WORKBOOK_SCHEMA) · `prompts/reuse/`.
Inherits `_SHARED_GUARD_BLOCK.md` (all applicable guards). Use after a cumulative master workbook + per-strain outputs exist.*

> **Note on scope:** the Top-N table is a STANDALONE deliverable, not a frozen master-workbook sheet.
> Do not write it into the frozen master schema; emit it as its own CSV/XLSX/HTML/MD/PDF + ZIP.

## Guard inheritance
Apply all applicable guards from `_SHARED_GUARD_BLOCK.md`. Separate source annotations and screening terms from validated chemistry. G4 concerns the bound run's actual evidence availability; the historical extraction-gap report does not establish a current defect or a lower-risk channel for this dataset. Check the version, receipt and available evidence before making comparisons or requesting any separately authorized source review.

## Task
Build a Top 50 halogenation-containing BGC deliverable from the cumulative dataset.
1. Filter BGCs with source-derived halogenation evidence: `T43-HAL` or halogenase in CCTT/marker
   fields; `halogenated`/`halogenase`/`polyhalogenated`/`chloro`/`bromo`/`iodo` in product/KCB text;
   candidate flavoprotein/halogenase terms (label as screening targets).
2. Rank by Sapote review priority. If <50 defensible candidates, report all and say so.
3. Per row: rank · strain · `strain / full node-or-contig / region / BGC alias` · products · halogenation lane/register ·
   halogenation evidence tier · exact evidence terms · boundary · architecture · assembly tier · genus ·
   host · AB/AF/novelty · Sapote priority score · KCB score + top hit · closest candidate KCB product ·
   MIBiG accession · similar-gene count + denominator (state which) · MIBiG URL · PubMed lookup URL ·
   literature status `UNVERIFIED — lookup only` · CCTT/marker triggers · RG-GMCI support · source GBK +
   length · claim-boundary note · one claim-safe why-interesting paragraph.
4. Outputs: CSV · XLSX · HTML · Markdown · no-overlap PDF card report · lane/assembly summary figures ·
   final ZIP.

## Required language
Use: candidate halogenation-containing BGC · source-derived T43-HAL signal · halogenation screening
target · closest candidate KCB product · consistent with · requires local gene/domain + LC-MS
isotope-pattern confirmation.
Avoid: produces chlorinated compound · confirmed halogenated product · halogenase confirmed by ChatGPT ·
exact PMID/DOI unless supported by a source-bound verification receipt (source, date and claim scope), whether from this session or a retained prior review.
