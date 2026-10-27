# REUSE PROMPT — Top 50 Polyketide-Containing BGCs (claim-safe)

> **Reuse status:** the v9.7.7 vetting label is historical. Bind the selected current contract, source version and actual package evidence before reuse. Apply the current shared guards; this template does not authorize extra scans, package mutation, external messaging or publication.
*Vetted against Sapote–Mamey v9.7.7 contract · `prompts/reuse/` · inherits `_SHARED_GUARD_BLOCK.md` (all applicable guards).
Use after a cumulative master workbook + per-strain outputs exist.*

> **G4 applies to the enediyne subfamily (required).** ene_KS (TIGR03828) is a TIGRFAM model. It lives only in the antiSMASH JSON, and the package carries it only if the record pass succeeded (see the `record_extraction` receipt). When you separate enediyne from hglE-KS, or count enediyne candidates, also read the raw genomic `antismash.detection.tigrfam` hits and reconcile them with the package. Do not conclude "no enediyne" from the package alone; a package-only count is a lower bound. Large modular PKS loci can also be fragmented across contigs and lose a diagnostic such as AHBA synthase, so for ansamycin-type polyketides apply both the G4 review and a fragmentation check. Keep raw-source observations beside the package; never edit sealed evidence.

## Task
Build a Top 50 polyketide-containing BGC deliverable from the cumulative dataset.
1. Filter BGCs whose product/marker fields contain: `PKS`, `T1PKS`, `T2PKS`, `T3PKS`, `HR-T2PKS`,
   `transAT-PKS`, `PKS-like`, `arylpolyene`, `hglE-KS`, `fatty_acid`.
2. Rank by Sapote review priority with assembly-aware guardrails: penalize Edge/Full-contig BGCs in
   POOR/VERY_POOR assemblies; do NOT auto-demote strong Interior/A BGCs solely because the strain
   assembly is poor. Label strain-level weighting as exploratory Sapote heuristic, not a monolith rule
   (G5).
3. Per row: rank · strain · `strain / full node-or-contig / region / BGC alias` · products · polyketide subfamily · boundary ·
   architecture · assembly tier · genus · host · AB · AF · novelty · Sapote lane/register · Sapote
   priority score · KCB score + top hit · closest candidate known natural product · closest MIBiG
   accession · similar-protein count + denominator (state query-CDS vs reference-cluster-gene) ·
   MIBiG URL · PubMed lookup URL `UNVERIFIED — lookup only` · CCTT/marker triggers · RG-GMCI support ·
   source GBK + length · claim-boundary note · one claim-safe why-interesting paragraph.
4. Outputs: CSV · XLSX · HTML · Markdown · no-overlap PDF card report · optional topology graphics for
   selected high-priority PKS BGCs · final ZIP.

## Required language
candidate polyketide-containing BGC · predicted BGC · source-derived KCB similarity · closest candidate
known natural product · consistent with · disambiguation target · requires domain-level + metabolomic
confirmation. Avoid: produces X · is X · confirmed enediyne · verified citation · PMID/DOI unless
supported by a source-bound verification receipt with source, date and claim scope; retain a valid prior receipt.
