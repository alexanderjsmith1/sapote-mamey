# Deliverable Contract — Plain English
**What Sapote must produce for every strain and why**

**v9.7.149a** | Source: `docs/DELIVERABLE_CONTRACT.md` | Last updated: 2026-06-29

---

## The core rule

At the point any strain reaches analysis-complete (all A1 extraction outputs present), Sapote must do ONE of:

1. **Auto-produce** the full per-strain deep-dive set, or
2. **Explicitly offer it** — a clear question asking whether to generate it, as the first item in the next-steps block

An analysis that stops at the workbook without surfacing the deep-dive set is an **incomplete delivery**. This is non-negotiable.

---

## Part A1: Mamey extraction outputs (what the engine produces)

These are produced deterministically by `mamey run`. Every item is required in the sealed package.

| File | What it contains |
|------|-----------------|
| `[strain]_1_intake.json` | Genome size, contigs, interior/edge/FC %, assembly tier, raw and corrected BGC counts |
| `[strain]_2_inventory.csv` | Every BGC with class, edge status, architecture confidence, KCB top hit, MIBiG %, WL score, bldA/TTA tier |
| `[strain]_2b_bgc_crosswalk.csv` | BGC_ID ↔ bgc_uid ↔ contig/region ↔ User_Label — the locator map |
| `[strain]_3_scan_states.json` | Status and output file for all source-derived scans; assembly block; package status |
| `[strain]_4A_RGGMCI_*.{csv,json}` | Split-BGC pairs (ClusterBlast/KnownClusterBlast); required for every multi-contig genome |
| `[strain]_4_triage_board.csv` | Per-BGC triage: CCTT triggers, primary-metab flag, standing rule, corrected rank |
| `[strain]_4B_Diagnostic_Rescue_*.{csv,json,md}` | Auto-emitted rescue leads + tiling |
| `[strain]_5_workbook.xlsx` | Per-strain workbook (coded sheets) |
| `[strain]_6_output_checklist.{csv,md}` | Per-run completeness checklist |
| `[strain]_7_cell_provenance.csv` | Status code per workbook cell (no silent blanks) |
| `[strain]_8_strain_brief.pdf` + `_8a…_8m_fig_*.png` + companion `_data.csv` | PDF brief binding all auto-emitted figures; each figure ships with its data CSV |
| `manifest.json` | Authoritative handoff object: all key findings, scan statuses, evidence pointers, version |
| `commit_receipt.json` | Run provenance / commit record |
| `issue_log.md` | Per-run issues and caveats |
| `checksums_sha256.txt` | SHA-256 for every file in the package |

---

## Part A2: Sapote interpretation documents (what you write)

These are the judgment-layer deliverables. They require a Sapote session with the sealed Mamey package.

### Layperson-Ranked BGC Guide

**Audience:** PI, student, collaborator

**Required sections:**
- Strain header block (ID, source, assembly tier, corrected BGC count)
- 2–3 sentence narrative (what the strain is, why it's interesting)
- Top-5 BGC ranked table with layperson headlines
- Assembly caveat (if POOR/VERY_POOR)
- Immediate next action (one concrete recommendation)

### Technical Full-Analysis Report

**Audience:** Natural-products specialist

**Required sections:**
- Intake and assembly/BGC summary
- All ten scan results
- Triage First Board (every BGC sorted by rank — POOR/VERY_POOR assemblies include edge/FC clusters)
- DAPR antibacterial and antifungal boards (separate)
- Full Mode B for HIGH/HIGH* BGCs
- Candidate cards for MEDIUM BGCs
- Wet-lab decision matrix
- Metabolomics readiness
- Fermentation card
- Ecology synthesis
- Cross-Strain Cohort Context block (see below)
- Method Caveats block (verbatim)
- Reviewer attack simulation
- Literature-Search Handoff list (for parallel ChatGPT run)
- PNAS reference list

### Compound Detection and Isolation Bench Guide

**Audience:** Bench scientist

Per-BGC bench protocol for HIGH and MEDIUM BGCs: detection method (UV, pigment, bioassay), extraction protocol, LC-MS method, isolation strategy — in plain English.

---

## Cross-Strain Cohort Context block (A2.1)

**Required in every per-strain deliverable.** Situates the single strain against the banked cohort.

Required contents:
- Corrected-BGC **rank in cohort** and assembly tier
- **Shared accessory chemistry** — each notable class with count of other strains carrying it (e.g. "T2PKS — shared with 13 others")
- **Strain-unique classes** in the cohort (provisional, sample-limited)
- **Novelty footprint** — this strain's KCB-dark region count as fraction of cohort total
- **Diagnostics carried** vs cohort

Source: `Strain_Cohort_Context` and `Cross_Strain_Class_Prevalence` workbook sheets.

Exclude the four universal classes (saccharide, fatty_acid, other, terpene) from shared/novel statements.

---

## Method Caveats block (A2.2) — verbatim in every deliverable

Include these verbatim. Never paraphrase.

> 1. `kcb_cumulative` is a cumulative **score, not a % identity** — a KCB hit anchors a class hypothesis, it does not mean the compound is known.
> 2. RG-GMCI HIGH-pair counts are **not a fragmentation-severity metric** — they track reference-anchored homologous-pair richness.
> 3. The four universal product classes are **non-discriminating** and are excluded from cross-strain shared/novel arguments.
> 4. `hglE-KS-PREV-001` is **collection-specific** — state it against the strain set it was measured on, never assume project-universal prevalence.

---

## The co-location mandate (A2.5)

In any compiled deliverable that pairs a locus map with its analysis, **each BGC is a single page-unit**:

```
Page layout (top to bottom):
1. Locus map (gene-arrow panel) — ~45% of page
2. Predicted class line — single line:
   "BGC_ID (contig · regionXXX) · predicted class: [class] · boundary: [status] · KCB: [similarity note]"
3. Mode B card (§1–§20 analysis) — remaining ~55%
```

**Rules:**
- Do NOT page-break between a locus map and its class line + Mode B card
- Only spill to a second page when Mode B genuinely overflows one page
- If it overflows: map stays with §1–§4; §5+ continue overleaf with "cont." marker

**Historical failure mode this prevents:** one locus map per page (rest of page blank) → Mode B prose pushed to following page. The map and its analysis must be readable as one unit.

---

## POOR/VERY_POOR equal-visibility rule (A2.6, v9.7.147)

For POOR and VERY_POOR assemblies: all BGCs are visible and included — sorted by score/rank, not by Interior-first. Edge and Full-contig BGCs are not buried or deprioritised relative to Interior BGCs in the deliverable display.

The assembly tier caveat appears in the header; it does not filter out clusters from the deliverable.

---

## Figure-ready tidy export (A2.4)

Ships alongside every deliverable set:

```bash
python tools/export_figure_ready.py <master_workbook.xlsx>
```

Produces `figure_ready/` folder with tidy CSVs — one observation per row, snake_case headers, no formulas. Contents:
- `strain_summary.csv` (one row/strain)
- `bgc_inventory.csv` (one row/BGC)
- `bgc_class_long.csv` (one row/BGC×class)
- `class_by_strain.csv` (one row/strain×class)
- `class_prevalence.csv` (one row/class)
- `diagnostics_long.csv` (one row/strain×TIGRFAM)
- `cross_strain_findings.csv`

Column names and types are versioned with the bundle — stable across runs.

---

## Verifying completeness

```bash
python tools/check_deliverable_suite.py \
  --manifest DELIVERABLE_MANIFEST_[strain].md
# Fails closed on unfilled items + JUDGMENT_PENDING gold gate
```

A deliverable with an unfilled DELIVERABLE_MANIFEST item is incomplete. Run `check_deliverable_suite.py` before handing over any deliverable set.

---

## Default delivery format

Default format is a **single consolidated PDF** — the colleague-facing hand-off format. Markdown and per-file outputs are alternatives. If the user has stated a standing preference (auto-generate, named subset, or format), honor it.

---

## See also

- **Authoritative source:** `docs/DELIVERABLE_CONTRACT.md`
- **Deliverable menu:** `docs/DELIVERABLE_MENU_v97146.md`
- **Completeness check:** `tools/check_deliverable_suite.py`
- **Judgment receipt/ingest:** `python -m mamey ingest-receipts`
- **Figure-ready export:** `tools/export_figure_ready.py`
- **Co-location spec:** `docs/PER_BGC_PAGE_LAYOUT_SPEC.md`
