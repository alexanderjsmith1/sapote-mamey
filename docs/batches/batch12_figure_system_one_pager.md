# Figure System One-Pager
**How to make, style, and deliver publication-ready figures**

**v9.7.149a** | Last updated: 2026-06-29

---

## Quick Start: "I want to make a figure. What do I do?"

1. **Check:** Does the figure already exist? See catalog below or `docs/FIGURES_START_HERE.md`
2. **Get data:** Run `export_figure_ready.py` to extract clean CSVs
3. **Render:** Run `build_figures.py` with those CSVs
4. **Style:** Figures auto-use house palette; manual tweaks in CSS/code if needed
5. **Export:** PNG + companion CSV (data transparency)

**Time:** ~5 minutes per figure.

---

## Figure Catalog

> **⚠ Note:** Figure IDs below (e.g. `fig_class_by_strain_heatmap`) are illustrative examples of the naming convention. The authoritative catalog with locked IDs and prompt links is in `docs/FIGURES_START_HERE.md` at the bundle root. Check there before building a figure — some of these may have different IDs or additional variants.

| Figure ID (example) | Name | What it shows | Input | Output |
|-----------|------|---------------|-------|--------|
| `fig_class_by_strain_heatmap` | BGC class distribution across strains | Rows=strains, Cols=class, Color=count | Cohort workbook | PNG heatmap |
| `fig_novelty_scatter` | Novelty vs. size scatter plot | X=BGC size, Y=novelty score, Color=class | Cohort workbook | PNG scatter |
| `fig_kbc_identity_distrib` | KCB identity % distribution | Histogram of KBC similarity scores | Cohort workbook | PNG histogram |
| `fig_ab_af_dual_scatter` | Antibacterial vs. antifungal scores | X=AB score, Y=AF score, Color=class | Cohort workbook | PNG scatter |
| `fig_assembly_tier_histogram` | Assembly quality distribution | Histogram of assembly tiers | Cohort workbook | PNG histogram |
| `fig_locus_map_<bgc_id>` | Gene topology for one BGC | Arrow diagram of genes/domains | Mamey package | PNG arrow map |
| `fig_domain_architecture` | Domain breakdown by class | Stacked bar: KS/AT/KR/A/T/E counts | Cohort workbook | PNG bar chart |
| `fig_pangenome_network` | BGC family network (pan-genome) | Nodes=BGCs, Edges=similarity | Cohort workbook | PNG/SVG network |
| `fig_corrected_vs_raw` | Assembly fragmentation impact | X=raw count, Y=corrected count | Assembly audit | PNG scatter |
| `fig_cctt_trigger_distribution` | Rare features across cohort | Bar chart of CCTT trigger counts | Cohort workbook | PNG bar |

**See also:** `docs/FIGURES_START_HERE.md` in bundle root (full catalog with links to prompts).

---

## House Style Rules

### Colors

> **⚠ Note:** The color values below are illustrative defaults consistent with typical Streptomyces natural product figure conventions. The authoritative locked palette is defined in `docs/FIGURE_STYLE.md` and the figure style module in the bundle. Always verify against those sources before submitting figures for publication.

| Element | Suggested color | Hex | Use |
|---------|----------------|-----|-----|
| **PKS** | Teal | #2E8B8B | Polyketide synthases |
| **NRPS** | Orange | #FF7F50 | Non-ribosomal peptide |
| **RiPP** | Purple | #9B59B6 | Ribosomally synthesized |
| **Terpene** | Forest Green | #228B22 | Isoprenoids |
| **Other/Unclassified** | Light Gray | #CCCCCC | Misc classes |

**Rule:** Use `docs/FIGURE_STYLE.md` as the single source of truth. The hex values above are starting points; pull the current locked values from the bundle before rendering publication figures.

---

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| **Axis labels** | Helvetica / Arial | 10 pt | Regular |
| **Titles** | Helvetica / Arial | 12 pt | Bold |
| **Legends** | Helvetica / Arial | 9 pt | Regular |
| **Strain names** | Monospace (Courier) | 9 pt | Regular |
| **BGC IDs** | Monospace (Courier) | 8 pt | Regular |

**Strain name format:** *Genus species* strain `ID` (italicize scientific name; backtick the ID)

---

### Layout & Spacing

- **Figure width:** 88 mm (single-column Nature / Science format)
- **Panel labels:** A, B, C, ... (top-left corner, bold, 12 pt)
- **Margin:** 10 mm around all edges
- **Panel spacing:** 5 mm between adjacent panels (for multi-panel figures)
- **Legend position:** Inside plot area (preferably lower-right), white box with 0.5 pt border

---

### Data Visualization Rules

| Plot type | Rules |
|-----------|-------|
| **Scatter** | Jitter x/y by ±5% to avoid overplotting. Size points by third dimension (if applicable). |
| **Heatmap** | Use diverging colormap (blue-white-red) if showing ±variation. Sequential colormap for positive-only data. |
| **Bar chart** | Order by value (descending). Add error bars if replicates available (SD or SEM). |
| **Histogram** | Use 20–30 bins. Add mean line (red, dashed) and median line (blue, dashed). |
| **Timeline/Phylo** | Monospace font for alignment/trees. Ladderize if phylogenetic. |

---

## Data Contract (figure_ready/ CSVs)

Every figure must have a **companion CSV** with the raw data.

**Structure:**

```csv
strain_id, bgc_id, contig, class, kbc_score, kbc_identity, ab_score, af_score, size_bp, novelty
SID8370, BGC_0001, contig_1, PKS, 8743, 45, 8.7, 6.2, 27300, 0.65
SID8370, BGC_0002, contig_2, NRPS, 5234, 52, 7.1, 8.3, 31500, 0.72
...
```

**Rules:**
- CSV = raw data, no calculations
- One row per data point
- All columns used in figure
- Strain names = `*Genus species* strain <ID>` (in caption, not CSV; CSV uses strain_id)
- Decimal places: 2 for scores, 0 for counts, 1 for %, 0 for bp

**File naming:** `fig_<figure_id>_data.csv` (e.g., `fig_ab_af_dual_scatter_data.csv`)

---

## When to Render Figures

### Automatic (Mamey does this)

After `mamey run --mode standard` or `--mode gold`:
- `locus_maps/` (gene topologies) — auto-rendered for all BGCs
- `figures/` (class distribution, etc.) — auto-rendered for strain overview

### On-demand (You run these)

1. **After Mamey:** `build_first_pass_scans.py` → quick triage heatmaps
2. **Before Mode B:** Optional; not required
3. **After Mode B + workbook merge:** `export_figure_ready.py` → `build_figures.py` → publication figures
4. **For presentation/thesis:** `build_master_figures.py` → atlas PDF
5. **For paper submission:** All figures + companion CSVs + captions (see below)

---

## Workflow: Mamey → Figures

```
mamey run --strain SID8370 --input-zip antismash.zip --mode gold
        ↓
✓ MAMEY_COMPLETE (locus_maps/ auto-generated)
        ↓
[Optional: build_first_pass_scans.py for quick pre-triage heatmaps]
        ↓
[If multi-strain:] hub_merge.py → merged master workbook
        ↓
export_figure_ready.py → figure_ready/ CSVs (edit these to adjust figures)
        ↓
build_figures.py --banked-dir cohort --workbook master.xlsx --out-dir figures/
  (generates 4 standard figures: chitinase_load, chitinase_normalization,
   chemistry_landscape, priority_leads_tierA)
        ↓
[Edit figure_ready/ CSV if needed, then --replot to regenerate without re-deriving]
        ↓
[Optional: build_panel_figure.py for multi-panel]
        ↓
✓ Figures ready for paper / presentation
```

---

## Figure Caption Template

**Format:**

```
Figure 1: [Title].
[A] Short sentence about panel A.
[B] Short sentence about panel B.
...
Abbreviations: BGC, biosynthetic gene cluster; PKS, polyketide synthase;
KCB, known cluster blast. Data are mean ± SD (n=X replicates). See
Supplementary Table Y for raw values.
```

**Example:**

```
Figure 2: BGC architecture and novelty across the SID cohort.
(A) Heatmap of biosynthetic class distribution (PKS, NRPS, RiPP, terpene)
across 20 Streptomyces strains. Color intensity indicates number of detected
clusters per class. (B) Scatter plot of BGC size versus novelty score,
colored by class. High novelty (>0.8) indicates rare/unknown pathways.
Data from 42 clusters across SID8370, SID8371, and SID8375. Raw data
available in Supplementary File S1 (fig_novelty_scatter_data.csv).
```

---

## Reproducibility Checklist

Before submitting figures, verify:

- [ ] Figure PNG file exists
- [ ] Companion CSV exists (with correct name: `fig_<id>_data.csv`)
- [ ] CSV contains all data points shown in figure
- [ ] Strain names in caption follow format: *Genus species* strain `ID`
- [ ] All colors match house palette (see above)
- [ ] Axis labels are clear and include units (e.g., "Size (kb)")
- [ ] Legend is present and readable
- [ ] No hardcoded strain IDs in figure (use numbers for anonymity; explain in caption)
- [ ] Figure was generated from code (`build_figures.py`), not manually edited

**Note:** Manually edited figures (drawn in PowerPoint, Adobe, etc.) don't meet reproducibility standard. Use code-generated figures.

---

## Common Figure Tasks

### Task: "I want a strain comparison heatmap"

> **Note on `build_figures.py` flags:** The real CLI accepts `--banked-dir`, `--workbook`, `--out-dir`, and `--replot`. It does not accept `--figure-type` or `--csv-dir`. The four built-in figures are: `chitinase_load`, `chitinase_normalization`, `chemistry_landscape`, and `priority_leads_tierA`. For figures outside these, use the prompt library (`prompts/figure_prompts/`) or write a custom script on top of the figure-ready CSVs.

```bash
# Data preparation — always run this first
python tools/export_figure_ready.py \
  --workbook merged_workbook.xlsx \
  --outdir figure_ready/

# Core figure generation (four built-in figures)
python tools/build_figures.py \
  --banked-dir cohort \
  --workbook merged_workbook.xlsx \
  --out-dir figures/

# Output: figures/ containing the four standard figures + companion data CSVs
```

---

### Task: "I want an interactive HTML atlas"

```bash
python tools/generate_bgc_atlas.py \
  --workbook merged_workbook.xlsx \
  --package-dirs runs/*/package/ \
  --figures figures/ \
  --outdir atlas/

# Output: atlas/index.html (self-contained, browsable in any browser)
```

---

### Task: "I want a figure for a presentation"

```bash
# Step 1: Export figure-ready data CSVs
python tools/export_figure_ready.py --workbook workbook.xlsx --outdir figure_ready/

# Step 2: Generate the four standard figures
python tools/build_figures.py \
  --banked-dir cohort \
  --workbook workbook.xlsx \
  --out-dir figures/

# Step 3: Replot after editing a CSV (e.g. to drop one strain)
python tools/build_figures.py --out-dir figures/ --replot

# Step 4: Compose a multi-panel figure
python tools/build_panel_figure.py \
  --panels figures/fig_1.png figures/fig_2.png figures/fig_3.png \
  --labels A B C \
  --outdir presentation/
```

---

### Task: "I want thesis diagrams"

```bash
python tools/build_thesis_diagrams.py \
  --strain SID8370 \
  --data strain_data.json \
  --outdir thesis_figures/

# Produces: cause-and-effect, chain-of-events diagrams
```

---

## Troubleshooting Figures

| Issue | Fix |
|-------|-----|
| Figures won't render (matplotlib error) | `pip install matplotlib numpy --break-system-packages` |
| Figures render but color is wrong | Check `figure_ready/` CSV has correct class labels; rebuild |
| Legend is cut off | Increase figure size in `build_figures.py` config (width/height params) |
| Strain names look weird | Check CSV format: should be `strain_id`, not full name; use strain_id in CSV |
| Data points don't match CSV | Re-run `export_figure_ready.py`; may be stale data |
| Can't find a figure ID | Check `docs/FIGURES_START_HERE.md` catalog; request new figure if not listed |

---

## File locations

| File | Purpose |
|------|---------|
| `docs/FIGURES_START_HERE.md` | Figure catalog + prompt library index |
| `prompts/figure_prompts/` | LLM prompts for each figure type |
| `prompts/figure_prompts/_INDEX.md` | Index of all figure prompts |
| `tools/build_figures.py` | Core rendering engine |
| `tools/export_figure_ready.py` | Data export tool |
| `tools/build_panel_figure.py` | Multi-panel composer |
| `tools/build_master_figures.py` | Atlas generator |
| `docs/FIGURE_STYLE.md` | Detailed style guide |
| `docs/FIGURE_REPRODUCIBILITY.md` | Reproducibility best practices |

---

## Quick commands (verified flags)

```bash
# Export figure-ready CSVs from workbook
python tools/export_figure_ready.py --workbook workbook.xlsx --outdir figure_ready/

# Generate four standard figures from cohort data
python tools/build_figures.py \
  --banked-dir cohort \
  --workbook workbook.xlsx \
  --out-dir figures/

# Replot from edited CSVs (no re-derivation)
python tools/build_figures.py --out-dir figures/ --replot

# Make a multi-panel composite
python tools/build_panel_figure.py \
  --panels figures/fig_a.png figures/fig_b.png \
  --labels A B \
  --outdir output/

# Build HTML atlas
python tools/generate_bgc_atlas.py \
  --workbook workbook.xlsx \
  --figures figures/ \
  --outdir atlas/
```

> **For figures not in the four built-in set:** use the prompt library (`prompts/figure_prompts/`) or `plot_examples.py` which renders from figure_ready/ CSVs and can be adapted for custom visualizations.

---

## Pro tips

1. **Always start with `export_figure_ready.py`.** It cleans your data and prevents figure errors.

2. **Keep companion CSVs.** They're your proof of reproducibility.

3. **Use strain IDs in CSVs, full names in captions.** Separates raw data from presentation.

4. **If a figure looks wrong, re-export + re-render.** Often fixes it without code changes.

5. **For presentations, use `build_master_figures.py` → PDF atlas.** Single file, all figures, easy to share.

---

## See also

- **Figure catalog:** `docs/FIGURES_START_HERE.md` (full index)
- **Figure style guide:** `docs/FIGURE_STYLE.md` (detailed rules)
- **Reproducibility:** `docs/FIGURE_REPRODUCIBILITY.md` (best practices)
- **Prompt library:** `prompts/figure_prompts/_INDEX.md` (LLM-assisted figure generation)

