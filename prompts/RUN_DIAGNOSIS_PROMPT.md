# RUN A STRAIN DIAGNOSIS — ChatGPT prompt
*Paste this with the Sapote–Mamey bundle + one or more antiSMASH ZIP(s). This is the normal
"diagnose a strain" path — no defect-hunting, no auditing.*

---

You have the Sapote–Mamey v9.7.414 bundle and one or more antiSMASH genome-mining ZIP(s).
Run the full pipeline and produce the diagnosis deliverables.

1. **Mamey extraction (deterministic):** run Mamey on each uploaded antiSMASH ZIP. Process every
   strain; append into one cumulative master workbook (key rows by Strain + BGC_ID; do not replace
   prior strains). Run the ten canonical scans: KCB sweep, RG-GMCI, FLBR, CCTT, CGAD, UMED, EFLS,
   resistance, bldA/TTA, TFBS.

2. **Read the evidence before judging:** for class calls, read
   `[StrainID]_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits` (per-locus HMM hits). NRPS
   substrate / active-site / RiPP-core / t2pks-class detail are now carried into the package by the
   evidence-conservation layer — read them from the parse's `nrps_pks_consensus`,
   `active_site_pairings`, `ripp_cores`, and `product_class_predictions` arrays (bounded/full
   json-evidence runs). Only fall back to the raw antiSMASH GBKs if a specific array is empty.

3. **Sapote interpretation:** strain-priority ranking, BGC-priority ranking, top antibacterial +
   antifungal leads (separate), full Mode B for HIGH BGCs, candidate cards for MEDIUM, ecology
   synthesis, wet-lab action board.

4. **Deliverables:** Layperson-Ranked BGC Guide, Technical Full-Analysis Report, Compound Detection
   & Isolation Bench Guide; cumulative master workbook; per-strain + batch summaries; manifest +
   checksums; final ZIP.

**Claim-safety (non-negotiable):** compound identities are genome-mining predictions — use
"candidate"/"predicted"/"consistent with", never "produces X" without isolation data. KCB is
similarity, not identity. Every BGC referenced as `BGC_ID (contig · regionXXX)`, never a bare ID.
Never emit an unverified PMID/DOI — use a PubMed search URL labeled `UNVERIFIED — lookup only`.
Flag missing evidence as `NEEDS_*` rather than guessing.
*(Canonical guard text: `prompts/reuse/_SHARED_GUARD_BLOCK.md` — G1–G5. This block restates it; if the two ever diverge, the shared block wins.)*

Report leads in chat as you go. Preserve all files with sensible names.
