# REUSE PROMPT — Top 50 Polyketide-Containing BGCs (claim-safe)
*Vetted against Sapote–Mamey v9.7.7 contract · `prompts/reuse/` · inherits `_SHARED_GUARD_BLOCK.md` (G1–G5).
Use after a cumulative master workbook + per-strain outputs exist.*

> ⚠ **ENEDIYNE SUBFAMILY IS TIGRFAM-AFFECTED (G4).** ene_KS (TIGR03828) is a TIGRFAM model and is
> dropped by the package extractor. When distinguishing enediyne from hglE-KS, or counting enediyne
> candidates, apply the G4 genomic-tigrfam fallback — do not conclude "no enediyne" from the package.
> Also note: the rifamycin case showed a large modular PKS can be FRAGMENTED across contigs and the
> AHBA diagnostic lost — so for ansamycin-type polyketides apply both G4 and a fragmentation check.

## Task
Build a Top 50 polyketide-containing BGC deliverable from the cumulative dataset.
1. Filter BGCs whose product/marker fields contain: `PKS`, `T1PKS`, `T2PKS`, `T3PKS`, `HR-T2PKS`,
   `transAT-PKS`, `PKS-like`, `arylpolyene`, `hglE-KS`, `fatty_acid`.
2. Rank by Sapote review priority with assembly-aware guardrails: penalize Edge/Full-contig BGCs in
   POOR/VERY_POOR assemblies; do NOT auto-demote strong Interior/A BGCs solely because the strain
   assembly is poor. Label strain-level weighting as exploratory Sapote heuristic, not a monolith rule
   (G5).
3. Per row: rank · strain · `BGC_ID (contig · regionXXX)` · products · polyketide subfamily · boundary ·
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
verified this session.
