# Strain BiG-SCAPE report and figure-label convention

Two standard deliverables, both DB-free (they read the portable derived TSVs, not the 400 MB DB).

## `tools/strain_bigscape_report.py` — per-strain report as a standard deliverable
Generates one strain's cross-strain / MIBiG-anchored biosynthetic report in the bundle's markdown
voice from the portable exports.

> **What the KNOWN / NOVEL and unique labels mean.** They are BiG-SCAPE family labels **within one run, at one
> cutoff, on the loaded panel and reference set**. KNOWN means the family contains a MIBiG member; NOVEL means
> it does not (`tools/bigscape_known_novel.py`). "Unique" or "cohort-exclusive" means no other loaded strain sits in
> the family. None of these labels identifies a compound, shows chemical novelty, or shows rarity in nature
> (`docs/BIGSCAPE_GCF_WORKFLOW.md`, caption rule). Always state the run, cutoff and panel denominator with any
> count. The field names stay as they are for the consumers that read them.

Detailed sections:
1. **Overview** — genus/habitat, BGC count, MIBiG-anchored / unanchored family split (the KNOWN/NOVEL labels), dominant class.
2. **Locator-derived contig summary** — span and upper-middle value of lengths parsed from selected per-BGC locator rows, plus the count below 15 kb. Repeated contigs are not deduplicated; only nonzero parseable lengths enter that denominator. These values do not independently establish assembly quality or fragmentation.
3. **BGC class distribution** — supplied class strings (blank becomes `?`), shown when counted at least twice or when the string contains PKS, NRPS or RiPP (case-insensitive). Other singleton classes are omitted; the table is not a full class census.
4. **Antimicrobial capacity** (from `--antimicrobial`) — antifungal (Candida) / antibacterial (MRSA) /
   siderophore anchors, capacity-level.
5. **MIBiG anchors** — nearest characterized cluster per KNOWN BGC, with antifungal/ionophore/over-broad
   flags, GCF distance, node.region, **and the antiSMASH domain architecture** (from `--integrated`).
6. **Notable BGCs** (from `--integrated`) — rows passing simple case-sensitive domain-word combinations (PKS_KS + PKS_AT + ACP/PP-binding, or Condensation + AMP-binding + PCP). The emitted “very likely” label also uses a parsed 15 kb contig threshold. These are display heuristics, not evidence of an intact pathway or function.
7. **Families without a MIBiG member** (from `--novel`; the legacy label is NOVEL) — antimicrobial-class families
   the strain is in that have no MIBiG member in this run, with the consensus assembly-line architecture. Not a novelty claim.
8. **Biosynthetic neighbors** (from `--sharing`) — closest strains by shared GCF families.
9. **Cohort-exclusive families** (from `--uniqueness`) — the strain's BGC count and fraction in families no other loaded strain occupies, with the panel denominator. This is similarity-family membership in this panel, not private chemistry.
10. **Caveats** — capacity-level, fragmentation, over-broad anchors, NAPAA exclusion.

The default output filename carries the strain ID. Display is bounded: at most 25 MIBiG anchor rows, 20 notable BGC rows, 15 unanchored-family rows and 8 neighbors. Long locators and domain text are shortened in selected tables. Preserve the full source tables and a bound strain / full node-or-contig / region / BGC alias crosswalk for individual-locus use; the Markdown alone is not a complete exact-identity export. No source database upload is needed.

```
python tools/strain_bigscape_report.py --strain AS-XXX \
    --per-bgc per_strain_BGC_annotation.tsv \
    --antimicrobial antimicrobial_capacity_by_strain.tsv \
    --novel novel_antimicrobial_targets.tsv --sharing strain_pair_shared_BGCs.tsv \
    --integrated antismash_bigscape_integrated.tsv \
    --genus Actinophytocola --habitat attine
```
Both `--strain` and `--per-bgc` are required. Optional tables are read only when their paths exist; a section also needs matching usable rows. A supplied path alone does not guarantee that its section is present.

## `tools/bigscape_figure_labels.py` — the type-strain vs MIBiG fix
Cohort **type strains** (classified `reference/type` by mamey_habitat_map) were legended as bare
"Reference", colliding with the **MIBiG reference** drawn in red. A gray node is a cohort strain; a
red node is a MIBiG cluster. This module is the single source of truth: type/reference taxa ->
**"type strain"** (gray), MIBiG -> **"MIBiG reference"** (red), host habitats unchanged. Bare
"reference" is guarded (`assert_not_bare_reference` raises). Import `category_of`, `STYLE`,
`legend_handles` in any figure builder.

## Not changed
- No data/clustering/anchoring change — the report reformats derived tables; the labels module governs
  display categories only. Report is markdown; render to docx/pdf downstream for a formal copy.

## Current legacy-consumer limits

This is a formatting consumer of pre-admitted portable TSVs. It has no run/cutoff selection option, no input/output hash receipt, and no full four-part locus validation. `--genus` and `--habitat` are caller-provided labels. Reconcile all input tables against one independently bound run, cutoff, cohort/reference roster and exact-locus crosswalk before building; do not combine exports by matching a bare family number or node.region string.

The implementation treats every selected per-BGC row whose status, after uppercasing without trimming whitespace, is not `KNOWN` as part of its displayed `NOVEL` count. Blank, held, unassigned, or unknown statuses therefore inflate that complement. Quarantine those rows or use a corrected status-aware export before interpreting the printed split. The generated phrase “have no analog” means only the computed complement in the loaded TSV; it is not supported evidence of no homolog, chemical novelty, or missing references. The generated MIBiG 4.0 subtitle is a literal label, not archive/version validation. Bind and correct the display to the actual reference version.

Optional input paths that do not exist are silently skipped, just as omitted inputs are. An absent section is not a biological negative. Missing output-parent directories are not created, and an existing output Markdown is overwritten. Use a fresh path with an existing parent, retain a source/output hash record, and check the section census against requested inputs.

The “very likely” / “likely” assembly-line labels are heuristic annotation labels based on domain words and boundaries, not functional proof. Preserve annotations as capacity evidence and remove unsupported biological-function wording from a reviewed copy while keeping the original provenance. Historical validation anecdotes above do not certify the current inputs or their scientific acceptance.

Source: `tools/strain_bigscape_report.py`.
