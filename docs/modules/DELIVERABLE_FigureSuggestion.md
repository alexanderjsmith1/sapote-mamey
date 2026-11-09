# DELIVERABLE: Figure Suggestion

**What this is.** A guide for choosing which figures to recommend in a strain's report. Choosing is judgment. This page covers the choosing and lists the tools that draw cohort-level figures. No listed tool draws a figure for one strain.

**Purpose.** For each recommended figure, state the purpose, the data, the visual form, where it goes, and what it must not imply.

[FIGURE_STYLE.md](../FIGURE_STYLE.md) and [FIGURE_REPRODUCIBILITY.md](../FIGURE_REPRODUCIBILITY.md) own the rendering rules (resolution, palette, fonts). The [deliverable contract](../DELIVERABLE_CONTRACT.md) wins over this page. Terms are in the [glossary](../GLOSSARY.md).

## When to use it

Add a "Recommended figures" section near the end of each complete strain report. A report with no figure section, or a recommendation with no claim-safety note, is incomplete.

## Which signal suggests which figure

| Signal in the finished analysis | Figure |
|---|---|
| 2 or more BGC fragments that probably form one pathway (RG-GMCI or LMPKS; see the [glossary](../GLOSSARY.md)) | Split-pathway schematic |
| An architecture A or B high-priority BGC | BGC architecture cartoon |
| Many BGCs with mixed novelty | KCB novelty scatter |
| 4 or more BGCs share a regulator family | TFBS regulatory heatmap |
| 5 or more plausible wet-lab targets | Wet-lab priority matrix |
| A genus or class seen in several habitats | Cross-habitat comparison |
| Several evidence streams for an ecological model | Ecological model figure |
| A very poor assembly shapes the interpretation | Assembly caveat figure |

Recommend a figure only when its data exists in the package. If the data is unscanned or absent, write "blocked pending <input>".

## Which tool draws what

| Tool | Draws |
|---|---|
| `tools/build_figures.py` | Cohort figures: `chitinase_load`, `chitinase_normalization`, `chemistry_landscape`, `priority_leads_tierA`, `contig_rescue`, `saccharide_adjusted` |
| `tools/build_panel_figure.py` | Composes existing single-panel PNGs (`--in-dir`, `--panels`, `--out`) into one figure. It draws nothing itself. |
| `tools/build_overview_figures.py` | Overview figures |
| `tools/build_workflow_figure.py` | The workflow figure |

None of these draws a per-strain figure, a split-pathway schematic or an architecture cartoon. The signals in the table above therefore give a recommendation to write down, not a figure these tools produce. Those figures need another renderer. Check `docs/FIGURES_START_HERE.md` for the current one.

## The command

```bash
python tools/build_figures.py --banked-dir <banked_dir> --workbook <master.xlsx> --out-dir <out_dir>
python tools/build_figures.py --out-dir <out_dir> --replot
```

`<banked_dir>` is a cohort folder of banked JSON files. `build_figures.py` needs three of them: `bgc_data.json`, `chitinase.json` and `bgc_markers.json`. `--workbook` must also be a real `.xlsx`. `tools/ingest_package.py --merge` writes `bgc_data.json` but not the other two, so a bank built only that way stops with `FileNotFoundError` on `chitinase.json`. `tools/chitinase_hmm_confirm.py` writes `chitinase.json` (it needs a proteome and a local Pfam-A.hmm). `tools/build_bgc_markers.py` writes `bgc_markers.json` (it also reads `deep_data.json`). Success is one line per figure ending in `.png + ..._data.csv`, then a `recipe` line, and exit 0.

The first command computes and plots. It refuses, with `refused:` and exit 2 before writing anything, when any of its outputs (each `<figure>_data.csv`, each `<figure>.png`, `figures_recipe.md`) already exists, so it never replaces a CSV you edited. Use a new `<out_dir>` for each compute run.

The second command redraws from the CSVs in `<out_dir>` after you edit them. It reads the CSVs and never writes them, but it replaces each figure's PNG and `figures_recipe.md` in place, so copy any earlier PNG you want to keep first. A figure whose CSV is missing gets a `[skip]` line; the run then prints `incomplete: N of 6 figures drawn; skipped (no CSV): ...` on stderr and exits 1. A PNG left in the folder from an earlier run is not proof that this run drew it; check the exit code and the lines printed.

## Template for one recommendation

```text
Figure X: <title>
Purpose: <what it shows>
Data needed: <BGC table, KCB, TFBS, domains, bioactivity>
Visual form: <schematic, heatmap, scatter, table, network>
Manuscript use: <Results, Discussion, Supplement>
Claim-safety note: <what the figure must not imply>
```

## Checklist

- [ ] Each recommendation has all six fields.
- [ ] Only figures with existing data are recommended.
- [ ] Rendered figures follow the style and reproducibility rules.
- [ ] Open holds are listed.

## Example

> Figure 1: Split-pathway schematic. Purpose: show fragments that may belong to one pathway. Data: RG-GMCI pairs for `<strain> / <full contig> / region<NNN> / <BGC alias>`. Form: schematic. Use: Supplement. Claim-safety: show domains, not a structure, and do not imply the fragments are joined.
