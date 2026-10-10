# Activity-lead deliverable reports

## Purpose

`tools/render_activity_lead_reports.py` turns the existing, upstream-generated
`mamey activity-leads` + `mamey activity-lead-genes` outputs into a single Day-5-shaped
deliverable: an assembly-quality tier table, a cross-strain best-targets table, then one card
per strain with a per-lead table carrying a Novelty figure, a Layperson headline, and a
Next-experiment suggestion. It computes no new score. Generated headlines and generic next-experiment text still require owner review; the renderer does not validate the upstream claims or approve experimental choices.

This is an authoring/reporting tool, standalone from the CLI (`tools/`, not wired into
`mamey/cli.py`). It is not a gate, and it never re-seals or edits a package.

## Inputs

| Flag | What it is | Produced by |
|---|---|---|
| `--runs-dir` | Root containing package triage boards and manifests; sealing is an operator requirement, not verified here | a normal `mamey run` |
| `--leads-dir` | Output dir of the activity-lead commands | `mamey activity-leads --out <dir>`, then optionally `mamey activity-lead-genes --out <dir>` |

`--runs-dir` is read only for assembly-quality bookkeeping (genome size, contig count, N50, and
the corrected-BGC / interior-% tier), using each strain's **full** triage board — the
activity-leads CSV only carries the top-N-per-axis subset, which is not enough to compute a
strain's true raw/interior/edge/full-contig counts.

The gene-anchor layer (`ACTIVITY_LEAD_GENE_ANCHORS.csv` / `ACTIVITY_LEAD_GENE_LOGIC.csv`) is
optional. A strain with routing leads but no bound gene table (activity-lead-genes held it —
see its own `ACTIVITY_LEAD_GENE_ANCHOR_HOLDS.csv`) still gets a full per-strain card; its
Layperson headline says plainly that the gene-level foundation was not evaluated, rather than
omitting the strain or guessing.

## Output

Always writes `<out>.md`. Writes `<out>.pdf` too when `reportlab` is importable, via the
bundle's own canonical Markdown-to-PDF renderer, `mamey.markdown_pdf` (the same renderer
`mamey.modeb_export` already uses for Mode B cards) — this tool does not implement its own PDF
layout. `--format markdown` forces Markdown-only even when `reportlab` is available;
`--format pdf` requires `reportlab` (raises if absent) instead of silently degrading.

Deterministic: every list is sorted on an explicit key (strain name, axis, rank, locus tag)
before being written. Output uses explicit sorting, but duplicate strain packages and duplicate summary keys can change which input is retained. Freeze the resolved input inventory and stamp before making a reproducibility claim.

## Field mapping (every "V2 contract" field is a pass-through, not a new value)

| Report field | Source | Notes |
|---|---|---|
| Locus | `exact_locus` (`activity_lead_report.py`) | `strain / full node-or-contig / region / bgc_alias` — the mandatory four-part identity |
| Class | derived from `Products` | normalized to the same NRPS/PKS/RiPP/terpene/siderophore/saccharide/beta-lactone/phosphonate buckets `activity_lead_genes._norm_class` already uses |
| Novelty | `Novelty_auto` | the engine's own re-projected novelty score (**higher = more novel**) — see "What does not match Day-5" below |
| Layperson headline | generated | class + `gene_logic_strength` (from `ACTIVITY_LEAD_GENE_LOGIC.csv`, when bound) + `interpretability_tier`/`interpretability_hold` |
| Next experiment | generated | a small, per-class, generic bench-method dictionary — never a compound-specific step |
| Gene anchors | `ACTIVITY_LEAD_GENE_ANCHORS.csv` | up to five genes per locus, unchanged from `activity_lead_genes.py`'s own selection and tier labels |
| Assembly tier | `mamey.assembly.assembly_tier` | GOOD/MODERATE/POOR/VERY_POOR, same thresholds (≥70/45–69/20–44/<20 interior %) |
| Corrected BGC count | `mamey.assembly.corrected_bgc_count` | Interior + 0.5×Edge + 0.25×Full-contig |

## Comparison against the Day-5 bar (`Layperson_BGC_Guide_All27Strains_BertMode_May2026.pdf`)

**What matches:** the document shape is the same three-part structure (tier table → cross-strain
best-targets table → per-strain cards), the tier definitions and the corrected-BGC formula are
byte-for-byte the same thresholds the engine already ships, every per-strain card carries a
Novelty figure, a Layperson headline, and a Next-experiment line per lead exactly as asked, and
anchored leads can carry a printed exact-locus heading and gene breakdown (≤5 named genes); unanchored leads do not reliably print that full identity —
Day-5 did not have gene-level anchoring at all; this is new ground the current engine's
`activity_lead_genes.py` makes possible that Day-5's May-2026 pipeline did not have.

**What does not match, and why (an honest scope limit, not an oversight):** Day-5's per-BGC
table carried a compound-class **structural analogue name** ("migrastatin/iso-migrastatin-like",
"HSAF/10-epi-HSAF") and a **MIBiG-percent-identity** figure, both hand-curated by a literature
pass (Bert Mode) against a specific top BLAST/KCB hit. Neither is present anywhere in the
current `activity_lead_report.py` / `activity_lead_genes.py` output surface: `KCB_top` is a bare
accession string ("BGC0000001 / navigation only"), not a compound name, and `Novelty_auto` is
the engine's own composite score (higher = more novel), not a MIBiG-similarity percentage — the
two are not interchangeable and this renderer does not attempt to fake one from the other. It
also does not carry a verified-citation library (Day-5's pages 14–16) — that is a distinct,
already-existing pipeline in this bundle (`Literature_Search_WorkOrder` / `Citation_Ledger`
under `mamey/citation_compact.py`, `mamey/validate.py::validate_citation_compact_outputs`), not
this tool's job to duplicate. Closing either gap for real (a compound-name lookup bound to a
verified citation, not an invented label) is future work for whichever lane owns that channel —
inventing either value here would be exactly the unsupported-specificity claim claim-safety
forbids.

## Claim-safety

Every BGC printed is a class-level routing hypothesis. `AF_auto`/`AB_auto` are routing priors,
never a measured activity. Gene anchors show class-explanatory biosynthetic logic, never
compound identity, production, or expression. Missing evidence is a workflow gap, not a
biological absence. This tool computes no new score, applies no new gate, and does not seal or
mutate any package. Judgment on every hypothesis is deferred to the Sapote (Tier 2/3) judgment
layer.

## Current admission and recovery limits

The renderer does not validate package sealing, upstream receipt hashes or lead schemas. Assembly bookkeeping recursively discovers triage boards; manifest absence or parse failure falls back to empty metadata, and repeated strain identifiers overwrite earlier entries. Gene summary keys also keep the last duplicate. Resolve package/strain ambiguity before report generation; preserve a file inventory and exact source hashes. Missing or malformed numeric fields can become zero in display/ranking helpers, so zero is not evidence that the underlying quantity was measured.

Cross-strain and per-lead tables print the BGC alias. Full `exact_locus` headings are printed only where gene anchors are present. This is a **full-identity hold** for unanchored or colliding leads. Until the renderer is revised, attach an exact-locus source index with strain / full node-or-contig / region / BGC alias and refuse alias-only adoption. The source field mapping above describes the intended identity, not universal printed coverage.

Generated next-experiment lines come from a static class dictionary. Treat them as unapproved authoring placeholders, not assay results or authorized experimental plans. Neither an upstream claim-safe format nor a successful render establishes scientific acceptance. The Day-5 comparison is historical context, not a current audit of the external PDF.

Markdown is written through a sibling temporary file and replacement; existing Markdown can be overwritten. PDF is attempted afterward and can fail after Markdown is published. Outputs are not a pair transaction, and the tool emits no source/output hash receipt. Use an unused output stem, inspect the returned `pdf_path`/`pdf_skipped_reason`, and inventory/hash the actual outputs separately. The low-level PDF call is not the Mode B profile verifier. A present PDF does not imply visual QA or current-profile approval.

Source: `tools/render_activity_lead_reports.py:149–245,288–289,366–429,455–505`.

## Example

```bash
python3 tools/render_activity_lead_reports.py \
  --runs-dir runs/ \
  --leads-dir runs/activity_leads/ \
  --out deliverables/activity_lead_reports/ACTIVITY_LEAD_REPORT \
  --top-n-targets 15
```

`--leads-dir` above is wherever `mamey activity-leads --out <dir>` (and, for gene anchors,
`mamey activity-lead-genes --leads <dir>/PER_STRAIN_ACTIVITY_LEADS.csv --out <dir>`) was pointed.
