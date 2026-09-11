# Compound detection and isolation bench guide — current format exemplar

This is a structure template. It contains no study result and no preselected culture, extraction,
chromatography, or assay condition. Build a guide from a validated package plus admitted chemical,
bioassay, literature, and phylogenetic evidence. Record missing evidence instead of completing a
field from a class stereotype.

## Evidence scope

| Input | Exact source/receipt | State | Permitted use |
|---|---|---|---|
| Sealed Mamey package | `[path or logical locator + SHA-256]` | `[validated/hold]` | Genome-derived capacity |
| Bioassay observation table | `[locator + SHA-256]` | `[admitted/holds]` | Activity at the recorded material and target level |
| LC-MS or fraction lineage | `[locator + receipt]` | `[verified/partial/unrecorded]` | Connect crude extract, flash fraction, HPLC fraction, and purified material |
| Phylogenetic result | `[GToTree or EPA-ng receipt]` | `[reviewed/hold]` | Taxonomic or ecological neighborhood context |
| Chemical reference | `[database record + structure ID + license]` | `[bound/hold]` | Comparator or class-member reference only |
| Literature | `[citation store row + acceptance state]` | `[source-verified/owner-accepted/hold]` | Support only the reviewed statement |

## Exact target identity

Every locus must appear as `strain / full node-or-contig / region / BGC alias`. Example placeholder:
`STRAIN-ID / FULL_CONTIG_ID / regionNNN / BGCNNN`. Do not use the alias alone in headings, tables,
filenames, or prose.

## Per-target bench card

### `STRAIN-ID / FULL_CONTIG_ID / regionNNN / BGCNNN` — `[capacity class]`

| Field | Entry |
|---|---|
| Boundary and assembly state | `[interior/edge/full-contig + source row]` |
| Gene/domain basis | `[specific admitted genes, domains, motifs, and holds]` |
| Comparator evidence | `[KnownClusterBlast / ClusterBlast / MIBiG / BLASTp, kept separate]` |
| Predicted chemical handles | `[formula, mass, adduct, UV, polarity only when source-bound]` |
| Reference structures | `[named reference/comparator + structure identifier; no product identity inference]` |
| Recorded assay context | `[material ID/type, lineage, organism state, time point, replicate, control state]` |
| Phylogenetic/ecological context | `[tree channel, neighborhood, metadata source, uncertainty]` |
| Immediate experiment | `[one bounded, testable action]` |

### Culture and induction matrix

| Condition ID | Medium | Temperature | Time | Aeration/format | Rationale source | Controls | State |
|---|---|---:|---:|---|---|---|---|
| `[condition-1]` | `[recorded formulation]` | `[value]` | `[value]` | `[value]` | `[citation or observed precedent]` | `[IDs/locations]` | `[planned/run/hold]` |

### Extraction and fraction lineage

| Material ID | Material type | Parent material | Lineage state | Extraction/fractionation step | Source record |
|---|---|---|---|---|---|
| `[material-1]` | `[CRUDE_EXTRACT/FLASH_FRACTION/HPLC_FRACTION/PURIFIED_COMPOUND]` | `[parent or n/a]` | `[VERIFIED/PARTIAL/UNRECORDED]` | `[recorded procedure]` | `[locator]` |

“Fraction plate” is a container label, not a material type. Identify each well's actual material and
parentage. Keep excluded or uncertain material as an explicit row with its reason.

### Assay plan and observations

| Experiment | Plate/well | Material | Target as recorded | Target state | Time point | Replicate | Control state | Result/disposition |
|---|---|---|---|---|---:|---|---|---|
| `[experiment-1]` | `[plate/A01]` | `[material-1]` | `[raw label]` | `[verified/ambiguous]` | `[hours]` | `[single/technical/biological]` | `[valid/hold]` | `[value/include/hold/exclude]` |

Do not fill a missing positive-control result with an expected optical-density value. Preserve
ambiguous *Candida* labels until resolved. Show separate experiments when pooling would hide
different material, target, time, replication, or control conditions.

### Ordered next experiment

1. `[First action and the evidence needed to proceed.]`
2. `[Second action conditional on the first result.]`
3. `[Confirmation or dereplication step.]`

### Interpretation boundary

State what the evidence supports at the locus, strain, material, fraction, and compound levels.
Recorded activity belongs to the tested material. A BGC-level activity statement requires a
separately admitted experimental link. A reference structure is visual context unless the assayed
material has been structurally identified.

## Cohort view

For multiple strains, compare the same defined endpoint. Name the target, material scope, time
point, aggregation, and included experiments. Keep `0` distinct from `NOT_MEASURED`; do not rank
strains by the maximum across non-uniform assay coverage.

The canonical observation and R-figure path is described in
[`docs/BIOASSAY_FIGURE_FACTORY.md`](../docs/BIOASSAY_FIGURE_FACTORY.md). Tree overlays use the same
selected endpoint through an exact strain/tip crosswalk.

