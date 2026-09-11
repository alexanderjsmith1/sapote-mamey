# HOW_TO_USE — figure-prompt library

This folder is a menu of figure-generation prompts for an LLM (Claude/ChatGPT) or a person.
Each `.md` is a self-contained spec: what figure, from which data, how encoded, with a suggested
caption and a separate list of overlay ideas to add downstream.

## Workflow
1. Produce the tidy data first: `python tools/export_figure_ready.py <master_workbook.xlsx>`
   → creates `figure_ready/` with the CSVs these prompts reference.
2. Pick a prompt from a category folder (or `_INDEX.md`).
3. Hand the prompt to the LLM, or implement it directly with matplotlib/ggplot. Every prompt's
   **Data** block names the exact file, columns, and row filter — no guessing which sheet.
4. Read `FIGURE_CONVENTIONS.md` once; it is inherited by all prompts (especially: no arrows on
   data points — overlays go on the slide).
5. Add emphasis (arrows, callouts, logos) downstream in PowerPoint / BioRender, using each
   prompt's **Overlay suggestions**.

## Categories
- `cohort/` — broad cross-genome views (the Sapote-Mamey signature: many genomes at once).
- `per_strain/` — single-strain figures for a deep-dive package or a spotlight slide.
- `novelty/` — KCB-dark / MIBiG-anchor / novelty figures.
- `ecological/` — TFBS and ecological-signal figures (Module 11 territory).
- `tables/` — slide-ready formatted tables (still "figures" for a deck).

## Modifying for consistency
Edit `FIGURE_CONVENTIONS.md` to change a rule globally; edit a prompt's **Data**/**Plot** blocks
to retarget it. Keep slugs and column names stable so downstream decks don't break.
