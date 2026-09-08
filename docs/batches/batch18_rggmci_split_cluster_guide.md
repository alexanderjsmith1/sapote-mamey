# RGGMCI Split-Cluster Guide
**How split BGCs work, how the rescue layer handles them, and how to write about them**

**v9.7.149a** | Source: `docs/GLOSSARY.md` §7, `*_4A_RGGMCI_*.csv` | Last updated: 2026-06-29

---

## The problem: fragmented assemblies split BGCs across contigs

A biosynthetic gene cluster can be 30–200 kilobases long. Short-read assemblies routinely produce contigs of 30–100 kb — which means a single BGC frequently gets cut into two or three fragments on different contigs. antiSMASH detects each fragment separately, treating them as independent clusters. Without rescue, you'd report 3 BGCs where one pathway actually exists.

This is what the FLBR → EFLS → RG-GMCI rescue chain exists to detect.

---

## The rescue chain: three tools working together

| Tool | Full name | What it does |
|------|-----------|-------------|
| **FLBR** | Fragment-Linkage BGC Recovery | Census of fragmented megasynthase (PKS/NRPS) sets across contigs — finds the fragments |
| **EFLS** | Edge-Flank Linkage Scan | Identifies split-pathway candidates at contig edges — locates the edges |
| **RG-GMCI** | Reference-Guided Genome Mining Candidate Inference | Proposes that two fragments share a reference producer cluster — infers the linkage |

None of these tools physically rejoins contigs at the nucleotide level. They produce **candidate inferences** — leads to chase, not proven joins.

---

## RG-GMCI in detail

**What it does:** Takes two BGC fragments on different contigs and asks: do they both match the same reference cluster in ClusterBlast/KnownClusterBlast? If yes, they might be two halves of one pathway.

**How it scores pairs:**

| Signal | Score contribution |
|--------|-------------------|
| Both fragments match the same MIBiG reference (KnownClusterBlast) | HIGH confidence |
| Both match same ClusterBlast reference (not in MIBiG) | MODERATE confidence |
| Only one fragment has a reference match | LOW confidence |
| Fragment pairs with >4 partners (promiscuous hub) | Demoted (guard) |
| Distant reference (dissimilar organisms) | Penalty applied |

**Output files:**
- `[strain]_4A_RGGMCI_full.json` — complete pair evidence
- `[strain]_4A_RGGMCI_ranked_pairs.csv` — pairs ranked by confidence
- `[strain]_4A_RGGMCI_evidence.csv` — per-pair evidence breakdown

---

## Key fields on the ranked pairs output

| Field | Meaning |
|-------|---------|
| `rggmci_score` | Numeric routing priority (not a claim-confidence score) |
| `rggmci_confidence` | HIGH / MODERATE / LOW |
| `db_kind` | Which database provided the reference: `knownclusterblast` (MIBiG), `clusterblast` (genomes), or `excluded subclusterblast` |
| `rescue_evidence_base` | BOTH_KCB_AND_CB / CLUSTERBLAST_ONLY / KNOWNCLUSTERBLAST_ONLY |
| `functional_rescue_class` | COMPLEMENTARY (fragments have different modules) / BOTH_CORE (overlap — may be paralogs) / ACCESSORY_ONLY (one fragment has only tailoring genes) |
| `subject_tiling_verdict` | COMPLEMENTARY_SPLIT / OVERLAPPING_PARALOG / AMBIGUOUS |
| `terminus_truncation_rescue` | Whether the v9.7.100 coordinate-based rescue triggered |

**COMPLEMENTARY_SPLIT** is the verdict you want — it means the two fragments cover different portions of the reference cluster, consistent with being two halves of one pathway. **OVERLAPPING_PARALOG** suggests the two fragments may instead be two copies of the same gene, not a split cluster.

---

## Claim ceiling

RG-GMCI is a **routing priority signal, not a claim**. The HIGH bonus (notionally +8) places the split-cluster candidate high in the triage board so it gets Mode B attention. It does not:
- Prove that the two fragments are physically one cluster
- License a compound-identity claim
- Override the corrected BGC count (split pairs are still counted as edge/full-contig fractions)

Physical confirmation requires long-read sequencing or gap-PCR across the break point.

---

## Corrected BGC count and split clusters

The corrected count formula (Interior × 1.0 + Edge × 0.5 + Full-contig × 0.25) is a **pre-rescue floor**. If RG-GMCI later shows two Edge fragments are one pathway, the biological cluster count is lower than the pre-rescue corrected count. The pre-rescue count is the defensible floor for reporting; note the RG-GMCI inference in parentheses when writing up.

**Example:**
> "Corrected BGC count: 38.25 equivalent (pre-rescue). RG-GMCI inference: BGC_0012 (contig_3 · region_003) and BGC_0019 (contig_7 · region_002) are candidate halves of a single trans-AT PKS pathway (HIGH confidence, MIBiG reference BGC0001234, COMPLEMENTARY_SPLIT). Post-rescue floor: 37.75 equivalent."

---

## How to cite split clusters in Mode B

The BGC locator rule is strict: every BGC must carry its contig and region in every mention. For split clusters, cite both fragments:

**First mention (full):**
> BGC_0012 (contig_3 · region_003) / BGC_0019 (contig_7 · region_002) — RG-GMCI pair, HIGH confidence

**Subsequent mentions within same section:**
> BGC_0012/BGC_0019 (split pair, region_003/region_002)

**Never:**
> The trans-AT PKS cluster BGC_0012 (bare ID without contig/region)

---

## Mode B card template for a split-cluster BGC

Add this banner at the top of the Mode B card when the BGC is part of an RG-GMCI pair:

```
⚠ SPLIT-CLUSTER CANDIDATE
BGC_0012 (contig_3 · region_003) is paired with BGC_0019 (contig_7 · region_002)
by RG-GMCI [confidence: HIGH | evidence: BOTH_KCB_AND_CB | verdict: COMPLEMENTARY_SPLIT]
Reference: ~MIBiG BGC0001234 (lydicamycin-class trans-AT PKS)
Physical proof of linkage requires long-read assembly or gap-PCR.
All claims in this card are bounded by the edge/full-contig caveat.
```

Then in §3 (biochemistry):
> "Domain architecture is assessed jointly across both fragments (BGC_0012 + BGC_0019). BGC_0012 carries KS, AT, and KR modules (consistent with elongation modules 1–6). BGC_0019 carries KS, DH, ER, and KR modules plus the terminal TE (consistent with elongation modules 7–11 + chain release). Together they span a complete trans-AT PKS consistent with a linear polyketide backbone."

And in §10 (Fragmentation and co-capture risks) of full Mode B:
> "Fragment concordance: COMPLEMENTARY_SPLIT verdict indicates the two fragments cover non-overlapping portions of the reference cluster. Co-capture risk (two unrelated BGCs sharing a comparator by coincidence) is LOW given the BOTH_KCB_AND_CB evidence base and the complementary domain distribution. Alternative: OVERLAPPING_PARALOG was explicitly tested by RG-GMCI and rejected."

---

## RGGMCI cohort rollup (multi-strain)

For cross-strain split-cluster analysis, use `rggmci_cohort_rollup.py`:

```bash
python tools/rggmci_cohort_rollup.py \
  --banked-dir cohort \
  --workbook master_workbook.xlsx \
  --outdir cohort_rggmci/
```

This produces a ranked cross-strain RGGMCI summary with confidence tiering — useful for identifying which split-cluster candidates appear repeatedly across strains (suggesting conserved but fragmented pathways).

---

## Common mistakes

**Treating COMPLEMENTARY_SPLIT as confirmed:** the verdict says the domain complement is consistent with a split pathway. Physical confirmation still requires sequencing.

**Counting the pair as one BGC in corrected count:** the corrected count formula operates pre-rescue. Report the pre-rescue floor, note the post-rescue inference separately.

**Forgetting to cite both BGC IDs:** every split-cluster mention in a deliverable must carry both BGC IDs with their contig/region locators.

**Missing the FLBR context:** RG-GMCI pairs often arise from FLBR-flagged LMPKS sets (large modular PKS fragments). Check the `_3_scan_states.json` FLBR block when interpreting a HIGH-confidence RG-GMCI pair.

---

## See also

- **Glossary entry:** `docs/GLOSSARY.md` §7 (RG-GMCI and the rescue layer)
- **Cohort rollup tool:** `tools/rggmci_cohort_rollup.py`
- **Reconstruction tool:** `tools/build_reconstruction.py`
- **FLBR census:** `docs/GLOSSARY.md` (FLBR entry)
- **Edge FASTA export for gap-PCR:** `tools/edge_fasta_export.py`
- **Dark gene rescue:** `tools/dark_gene_scan.py`
