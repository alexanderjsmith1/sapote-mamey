# REUSE PROMPT — Fragment-Rescue Run (RG-GMCI / FLBR / EFLS)
**Vetted against:** Sapote–Mamey v9.7.7 contract · monolith §42 (LMPKS), §51 (FLBR), §52 (UMED), and the
RG-GMCI / EFLS scan definitions in `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` + `docs/WORKBOOK_SCHEMA.md`.
**Use:** when a fragmented assembly (MODERATE/POOR tier, many Edge/Full-contig BGCs) needs cross-contig
pathway reconstruction — recovering split megasynthases and constellations the per-region view misses.

---

## Role & preconditions
Sapote layer over a sealed Mamey package. Do not re-run scans. First:
1. Confirm package integrity (gate + checksums).
2. **Read `[StrainID]_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits` for every fragment locus before
   asserting linkage** — a split KS/A-domain is only evidence if the per-locus HMM hits support it.
3. Pull the RG-GMCI files: `4A_RGGMCI_full.json`, `4A_RGGMCI_ranked_pairs.csv`, `4A_RGGMCI_evidence.csv`;
   plus FLBR and EFLS states from scan_states.

## What to produce
- **Fragment census (FLBR §51):** megasynthase fragments — split NRPS/PKS modules across contigs.
  Report per-fragment: locus, contig, domain content (from gbk_pfam_hits), module-completeness call.
- **RG-GMCI promoted groups:** evaluate ranked pairs; promote a cross-contig group to a candidate
  reconstructed pathway ONLY when evidence tier + shared-signature support it. Each promoted group gets
  a claim ceiling (LinkageConfidence: HIGH interior/contiguous · MODERATE edge/probable · LOW
  cross-contig/EFLS-rescued · UNRESOLVED). Populate D3_RGGMCI_Promoted (Sapote-owned).
- **LMPKS rescue (§42):** for large modular PKS, the linear-polyether/ionophore detection pass
  (epoxidase + epoxide hydrolase cassette). State the detection-reality caveat (some tailoring enzymes
  are HMMER-pending).
- **EFLS cross-contig linkage:** candidate flanking-locus pairs supporting the above.

## Non-negotiable rules
- **Fragmentation ≠ disqualification** (monolith principle): a fragment can be HIGH priority; assembly
  state lowers product-identity confidence, not necessarily lead value.
- **Claim-safety + locator mandate** as in the deliverables prompt: every BGC/fragment as
  `BGC_ID (contig · regionXXX)`; candidate language only; mark `EVIDENCE_PENDING` where HMMER/long-read
  would be needed to confirm a join.
- **Never assert a cross-contig join as physical fact** — it is a reconstruction hypothesis until
  long-read assembly or PCR confirms; say so.
- Promoted groups feed D3; do not write them into B1_BGC_Master as if single-locus.

## Handback
RG-GMCI promoted-group table (with claim ceilings) + fragment census + LMPKS rescue findings +
D3 deltas. Note which joins are long-read-confirmable. End with exactly 8 unique numbered next paths.
