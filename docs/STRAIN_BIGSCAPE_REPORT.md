# Strain BiG-SCAPE report + figure-label convention (v9.7.293)

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
2. **Assembly quality** — contig-size span, median, and the count of BGCs on <15 kb contigs, with the
   fragmentation caveat stated up front (per-region hits are fragments until a contiguous assembly confirms).
3. **BGC class distribution** — full antiSMASH class counts.
4. **Antimicrobial capacity** (from `--antimicrobial`) — antifungal (Candida) / antibacterial (MRSA) /
   siderophore anchors, capacity-level.
5. **MIBiG anchors** — nearest characterized cluster per KNOWN BGC, with antifungal/ionophore/over-broad
   flags, GCF distance, node.region, **and the antiSMASH domain architecture** (from `--integrated`).
6. **Notable BGCs** (from `--integrated`) — the strain's clusters with a complete core assembly line
   (PKS: KS+AT+ACP; NRPS: C+A+PCP), the ones most likely functional and worth prioritising.
7. **Families without a MIBiG member** (from `--novel`; the legacy label is NOVEL) — antimicrobial-class families
   the strain is in that have no MIBiG member in this run, with the consensus assembly-line architecture. Not a novelty claim.
8. **Biosynthetic neighbours** (from `--sharing`) — closest strains by shared GCF families.
9. **Cohort-exclusive families** (from `--uniqueness`) — the strain's BGC count and fraction in families no other loaded strain occupies, with the panel denominator. This is similarity-family membership in this panel, not private chemistry.
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

## Current legacy-consumer limits

This is a formatting consumer of pre-admitted portable TSVs. It has no run/cutoff selection option, no input/output hash receipt, and no full four-part locus validation. `--genus` and `--habitat` are caller-provided labels. Reconcile all input tables against one independently bound run, cutoff, cohort/reference roster and exact-locus crosswalk before building; do not combine exports by matching a bare family number or node.region string.

The implementation treats every selected per-BGC row whose status is not exactly `KNOWN` as part of its displayed `NOVEL` count. Blank, held, unassigned, or unknown statuses therefore inflate that complement. Quarantine those rows or use a corrected status-aware export before interpreting the printed split. The generated phrase “have no analog” means only the computed complement in the loaded TSV; it is not supported evidence of no homolog, chemical novelty, or missing references. The generated MIBiG 4.0 subtitle is a literal label, not archive/version validation. Bind and correct the display to the actual reference version.

Optional input paths that do not exist are silently skipped, just as omitted inputs are. An absent section is not a biological negative. Missing output-parent directories are not created, and an existing output Markdown is overwritten. Use a fresh path with an existing parent, retain a source/output hash record, and check the section census against requested inputs.

The “very likely” / “likely” assembly-line labels are heuristic annotation labels based on domain words and boundaries, not functional proof. Preserve annotations as capacity evidence and remove unsupported biological-function wording from a reviewed copy while keeping the original provenance. Historical validation anecdotes above do not certify the current inputs or their scientific acceptance.

Source owner: `tools/strain_bigscape_report.py:68–104,117–122,148–198,218–254,282–285`.
