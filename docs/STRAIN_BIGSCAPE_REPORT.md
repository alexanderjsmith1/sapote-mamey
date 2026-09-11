# Strain BiG-SCAPE report + figure-label convention (v9.7.293)

Two standard deliverables, both DB-free (they read the portable derived TSVs, not the 400 MB DB).

## `tools/strain_bigscape_report.py` — per-strain report as a standard deliverable
Generates one strain's cross-strain / MIBiG-anchored biosynthetic report in the bundle's markdown
voice from the portable exports. Detailed sections:
1. **Overview** — genus/habitat, BGC count, known/novel split, dominant class.
2. **Assembly quality** — contig-size span, median, and the count of BGCs on <15 kb contigs, with the
   fragmentation caveat stated up front (per-region hits are fragments until a contiguous assembly confirms).
3. **BGC class distribution** — full antiSMASH class counts.
4. **Antimicrobial capacity** (from `--antimicrobial`) — antifungal (Candida) / antibacterial (MRSA) /
   siderophore anchors, capacity-level.
5. **MIBiG anchors** — nearest characterized cluster per KNOWN BGC, with antifungal/ionophore/over-broad
   flags, GCF distance, node.region, **and the antiSMASH domain architecture** (from `--integrated`).
6. **Notable BGCs** (from `--integrated`) — the strain's clusters with a complete core assembly line
   (PKS: KS+AT+ACP; NRPS: C+A+PCP), the ones most likely functional and worth prioritising.
7. **Novel families** (from `--novel`) — novel antimicrobial-class families the strain is in, with the
   consensus assembly-line architecture.
8. **Biosynthetic neighbours** (from `--sharing`) — closest strains by shared GCF families.
9. **Uniqueness** (from `--uniqueness`) — strain-unique BGC count + fraction (families no other cohort strain occupies) = private chemistry.
10. **Caveats** — capacity-level, fragmentation, over-broad anchors, NAPAA exclusion.

Filename carries the strain ID (bundle convention). Capacity-level throughout; node.region locators;
no compound-production or per-BGC bioactivity claims. Runs anywhere the AS_analysis_export bundle
reaches — no DB upload.

```
python tools/strain_bigscape_report.py --strain AS-XXX \
    --per-bgc per_strain_BGC_annotation.tsv \
    --antimicrobial antimicrobial_capacity_by_strain.tsv \
    --novel novel_antimicrobial_targets.tsv --sharing strain_pair_shared_BGCs.tsv \
    --integrated antismash_bigscape_integrated.tsv \
    --genus Actinophytocola --habitat attine
```
Verified on the real 51-strain export against one cohort strain's hand-built report — BGC counts,
known/novel split, class tallies, contig-size profile, assembly-line count, and capacity calls all
matched exactly. (v9.7.372: the per-strain numbers previously quoted here are unpublished cohort
results, withheld from the public code tier; a public type-strain worked example follows.) Only `--per-bgc` is required; every
other input adds a section if supplied and is skipped cleanly if not.

## `tools/bigscape_figure_labels.py` — the type-strain vs MIBiG fix
Cohort **type strains** (classified `reference/type` by mamey_habitat_map) were legended as bare
"Reference", colliding with the **MIBiG reference** drawn in red. A grey node is a cohort strain; a
red node is a MIBiG cluster. This module is the single source of truth: type/reference taxa ->
**"type strain"** (grey), MIBiG -> **"MIBiG reference"** (red), host habitats unchanged. Bare
"reference" is guarded (`assert_not_bare_reference` raises). Import `category_of`, `STYLE`,
`legend_handles` in any figure builder.

## Not changed
- No data/clustering/anchoring change — the report reformats derived tables; the labels module governs
  display categories only. Report is markdown; render to docx/pdf downstream for a formal copy.
