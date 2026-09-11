# DELIVERABLE — Figure Suggestion (FIG)

> **Filing.** `docs/modules/DELIVERABLE_FigureSuggestion.md`.
> **Extends / references:** `tools/build_figures.py`, `tools/build_panel_figure.py`, `tools/build_overview_figures.py`, `tools/build_workflow_figure.py` (the figure *builders*), `FIGURE_STYLE.md` + `FIGURE_REPRODUCIBILITY.md` (style/repro rules — **do not restate**), `DELIVERABLE_CONTRACT.md`.
> **Precedence.** Parent monolith wins; `FIGURE_STYLE.md`/`FIGURE_REPRODUCIBILITY.md` win on rendering. This module owns only the *recommendation logic* (which figures this strain warrants).
> **Status:** `PROMPT_BACKED` (Sapote recommends; the builder tools render). The split is deliberate — recommendation is judgment, rendering is code.
> **One-line purpose.** Recommend the figures that would support a manuscript/talk for *this* strain, each with purpose, data source, visual form, manuscript placement, and a claim-safety note — closing the gap between "we have figure tools" and "which figures does this strain need."

---

## 1. When it is offered (Deliverable Offer Protocol)

Auto-append a `Recommended Figures from This Analysis` section near the end of every complete strain report. Offer as a next-path when a report is complete but no figure recommendations were made. **Incomplete delivery** = a finished strain report with no figure section, or a recommendation with no claim-safety note.

---

## 2. Inputs required

| Signal (from the completed analysis) | Triggers the figure |
|---|---|
| ≥2 BGC fragments likely one pathway (RGGMCI / LMPKS) | Split-pathway schematic |
| Architecture A/B high-priority BGC | BGC architecture cartoon |
| many BGCs, mixed novelty (KCB/RiQ) | KCB/RiQ novelty scatter |
| ≥4 BGCs share a regulator family (TFBS) | TFBS regulatory heatmap |
| ≥5 plausible wet-lab targets | Wet-lab priority matrix |
| genus/class in multiple habitat categories | Cross-habitat comparison |
| strong ecological synthesis, multiple evidence streams | Ecological model figure |
| very poor assembly drives interpretation | Missingness/assembly caveat figure |

**Skip-not-fake.** Recommend only figures whose underlying data actually exists in the package; a figure whose data is `unscanned`/absent is not recommended, or is recommended explicitly as "blocked pending [input]."

---

## 3. Pipeline

`PROMPT_BACKED` recommendation → hand to the matching builder tool for rendering:
```bash
python tools/build_figures.py --package-dir <pkg> --figure <type> --out-dir <dir>   # honors --replot --dpi
```
Rendering rules (DPI, palette, fonts, reproducibility manifest) are owned by `FIGURE_STYLE.md` / `FIGURE_REPRODUCIBILITY.md` — this module does not restate them.

---

## 3a. Recommendation template (§39.4)

```text
Figure [X] — [Title]
Purpose: [what it communicates]
Data needed: [BGC table / KCB / TFBS / domains / bioactivity]
Recommended visual form: [schematic / heatmap / scatter / table / network]
Manuscript use: [Results / Discussion / Supplement]
Claim-safety note: [what the figure must NOT imply]
```

---

## 4. Outputs & contract surface

A `Recommended Figures` section in the strain report (the recommendations) + any rendered figures the builders produce (registered per `FIGURE_REPRODUCIBILITY.md`, not hand-edited).

---

## 5. Acceptance checklist

- [ ] Each recommendation has all six template fields, including the claim-safety note.
- [ ] Only figures with existing data are recommended (skip-not-fake).
- [ ] Rendered figures defer to `FIGURE_STYLE.md`/`FIGURE_REPRODUCIBILITY.md`; not restated here.
- [ ] Contig-ID locators on any BGC referenced; affiliation = ; exactly 8 unique next-paths.

---

## 6. Tool / knowledge inventory

| Piece | Owner |
|---|---|
| Recommendation logic | this module |
| Figure rendering | `tools/build_figures.py` & siblings |
| Style / reproducibility | `FIGURE_STYLE.md`, `FIGURE_REPRODUCIBILITY.md` |

---

## 7. Worked next-paths closer (SID-XXX)

> Recommended figures: (1) Split-pathway schematic — 017/035/072 NRPS-PKS megaset (Supplement); (2) KCB/RiQ novelty scatter — 75 BGCs, mixed novelty (Results); (3) Wet-lab priority matrix — 12 leads (Results); (4) BGC architecture cartoon — BGC047 enediyne (Results), claim-safety: show domains, not a structure. Next paths:
> 1. Render figures 1–4 via `build_figures.py`.
> 2. Add a missingness/assembly-caveat figure (POOR tier drives interpretation).
> 3. Hold the enediyne cartoon to domain-level depiction only.
> 4. Once a 2nd Amycolatopsis is banked, add a cross-habitat comparison.
> 5. Register all rendered figures per FIGURE_REPRODUCIBILITY.
