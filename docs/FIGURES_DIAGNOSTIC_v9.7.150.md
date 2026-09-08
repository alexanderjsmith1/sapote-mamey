# Figures pipeline — diagnostic findings (v9.7.150)

> **SUPERSEDED (v9.7.409) — `--mode smoke` no longer runs.** `smoke` was removed at v9.7.161;
> `mamey run` now accepts only `{standard,gold}` and rejects `smoke` with an argparse
> `invalid choice` error. Gold is the only analysis mode. Current first-run one-liner:
> `python -m mamey run --mode gold --capped-session --json-evidence off`. The figure-count
> observations below describe the historical default-run behavior and are kept for provenance.

**Authored:** 2026-06-30 (Opus audit chat)
**Trigger:** "the figures are basically nonexistent"
**Verdict:** The complaint is structurally accurate for the typical single-strain workflow. The figure modules exist in code but most are gated behind `gold` mode or explicit `mamey render-figures --figure-set <X>` invocations. A default `mamey run` (the common starting point) historically produced only **3 PNGs + a variable number of locus map SVGs**. That is the entire automatic figure output. Everything else requires extra commands the working chat may not know to run.

This is a **separate concern from the W9 structure-gate firebreak**. Recording findings here so the figures work doesn't get tangled with the contract-enforcement cut.

---

## What actually fires by default

### `mamey run` (default first-pass; historically invoked as `--mode smoke`)

Auto-fires inside `run_one_strain()`:

1. **`figures_smoke.generate()`** (W2; cli.py:1684) — produces **3 PNGs** in `<pkg>/smoke_figures/`:
   - `bgc_ranking.png` — top-15 BGCs by region length
   - `class_composition.png` — class distribution
   - `assembly_tier.png` — interior/edge tier breakdown
   - Plus a `_data.csv` per figure (per standing rule)
   - Non-blocking; matplotlib-required; if matplotlib missing, prints "skipped".

2. **`locus_map.render_locus_map()`** (cli.py:790) — fires only **if a source GBK zip is on disk AND `--locus-maps auto`**. The W5 ingest path I built (`render_for_compile_report`) populates these too from the gene-by-gene CSV, but only at `mamey compile-report` time, not during `mamey run`.

3. **Nothing else.** The 13 other figure modules (cohort_figures, domain_figures, cross_strain_figures, master_figure_atlas, figures_extra, figures_sapote, figures_split, collection_figures, mamey_native_figures, cohort_figures_d, cohort_figures_g, cohort_figure_captions, figure_policy) do not fire in smoke mode.

### `mamey run --mode standard`

Same as smoke. The "standard" mode (back-compat alias for "gold" downstream per v9.7.92+) still does not auto-fire cohort/gold figures because the `if mode == "gold"` check at cli.py:1292 only matches the literal string `"gold"`.

### `mamey run --mode gold`

In addition to the above, fires:

4. **`cohort_figures.generate()`** (cli.py:1295) → `<pkg>/gold_figures/`. This produces the rich figure suite (heatmaps, ranking dotplots, class panels, etc.) — **but only when the inferred `runs_dir` actually contains multiple package-like subdirectories** (cli.py:1303). For a single-strain run, the inference often falls back to the immediate parent dir, which works but with reduced cross-strain context.

### `mamey compile-report`

Walks `<pkg>/**/*.png` and (post-N3) `*.svg`. If smoke_figures + locus_maps emitted files during the run, compile-report references them in §6. If they didn't, the §6 figures section says "no figures in package" (the fallback `_try_generate_figures` then attempts a best-effort smoke re-run — non-blocking).

---

## Why this looks like "basically nothing"

The 3-figure smoke baseline + variable locus maps is small for what the deliverable contract expects. A typical Sapote–Mamey strain analysis is supposed to surface (per `SESSION_START_MANIFEST.md` §0.6):

- `_8a…_8m_fig_*.png` plus companion `_data.csv` files — **none of these auto-generate from `mamey run` in any mode**; they require either `tools/build_first_pass_scans.py --package <pkg>` (renders 8 first-pass-scan figures) or `mamey render-figures` with the right `--figure-set`.

This is a documentation + automation gap, not a code gap. The figures *exist as code* — they just don't *fire automatically*. A chat following the manifest's "MAMEY_COMPLETE handback" instructions has to know to run extra commands to populate the figure suite.

---

## Specific gaps and fixes

### Gap 1 — `figures_smoke` produces only 3 figures

The wishlist W2 (now landed) defined exactly three figures: BGC ranking, class composition, assembly tier. That was deliberate — smoke mode is meant to be fast. But "the figures" in normal usage is the 8 `_8a…_8m_fig_*.png` suite from `tools/build_first_pass_scans.py`.

**Fix:** wire `tools/build_first_pass_scans.py` (or its equivalent in `mamey/` — likely `mamey.first_pass_scans` if it exists) into the smoke-mode auto-figure path so the 8-figure suite fires by default. Verify the module exists; if not, the figures listed in the deliverable contract are aspirational not realized.

**Investigation needed:** does `mamey/source_scans.py` exist? Does it have a callable that produces those 8 PNGs from CSVs already on disk? If yes, wire it into `run_one_strain()` alongside `figures_smoke`. If no, the deliverable contract over-promises and the gap is real.

**[ANSWERED, v9.7.213 audit, 2026-07-06]:** No — *mamey/first_pass_scans.py* does not exist (verified: `find . -iname "*first_pass_scans*"` in the live .213 tree returns only `tools/build_first_pass_scans.py` and its test). The gap this doc describes is real but has a different resolution than either branch above: `SESSION_START_MANIFEST.md` §0.5 documents `mamey render-all-figures --package <pkg> [--all --workbook <wb.xlsx>]` (landed v9.7.150e+, the same version window this diagnostic is dated to) as the aggregate post-seal command — i.e. Gap 1's requested fix ("Add `mamey render-all-figures` aggregate command," item 2 below) appears to have landed under that name around the time this doc was written. Not independently re-verified end-to-end against a real package in this audit pass; flagging as likely-resolved rather than confirmed-resolved.

### Gap 2 — `cohort_figures` only fires in gold mode

For single-strain analyses in standard or smoke mode, the rich figure suite is invisible. The check `if mode == "gold"` could be loosened to `if mode in {"gold", "standard"}` — cohort_figures has the same dependencies as the smoke set (matplotlib + CSVs already on disk), so there's no engineering reason it can't fire in standard mode too.

**Fix:** add `standard` to the cohort_figures auto-fire condition. Make it non-blocking the same way smoke_figures is.

### Gap 3 — `render-figures` is a per-set command, not a "render everything"

`mamey render-figures --figure-set X` requires a separate invocation per figure set. The chat has to know about each (`standard`, `domain-level`, `locus-maps`, `cohort-class`, `mamey-native`). There's no "render the full deliverable suite" command.

**Fix:** add `mamey render-all-figures --package <pkg> [--workbook <wb.xlsx>]` that iterates through every figure-set and emits everything matplotlib + the available data can produce. Non-blocking per set. Prints a summary of what landed.

### Gap 4 — `figure_policy.py` exists but is silent

`mamey/figure_policy.py` looks like it was designed to govern which figures fire when — but it's never imported by cli.py or the run pipeline (verified via grep). Either it's the planned mechanism for fixing Gap 2/3 and was never wired in, or it's dead code that should be retired or surfaced.

**Investigation needed:** read `figure_policy.py` and decide whether it's the right home for an auto-figure-suite contract, or whether it should be deleted.

### Gap 5 — `locus_renderer_v2` (publication-grade SVG/PNG) exists but only `directed_studies/pks.py` (external, not shipped in this bundle) uses it

`mamey/figures/locus_renderer_v2.py` claims to be "publication-grade, evidence-gated vector locus renderer." It's marked as a P0 legacy feature in `legacy_feature_gate.py:77` with status "active". But it's called only from one directed-study module, not from the standard locus_map pipeline.

**Decision needed:** either promote v2 as the default locus renderer (replace `locus_map.render_locus_map()` calls), retire it, or document why it's a directed-study-only path.

---

## Recommended next session: figures cleanup

Three small commits + one larger one, in order:

1. **Loosen cohort_figures auto-fire to include standard mode.** One-line change to the `if mode == "gold"` guard in cli.py:1292. Adds ~15-20 PNGs to a default standard-mode run. Low risk — non-blocking per-failure.

2. **Add `mamey render-all-figures` aggregate command.** Iterates every figure set, prints a summary. Lets the chat run one command to populate the full figure suite post-seal.

3. **Audit `mamey/source_scans.py`** (if it exists) and wire it into the run path so the 8 deliverable-contract PNGs fire automatically. If the module doesn't exist, the deliverable contract needs updating — flag it.

4. **Decide the fate of `figure_policy.py` and `locus_renderer_v2.py`.** Either wire them in or retire them — they're cargo-cult code right now.

These together transform the default-run figure output from "3 PNGs" to "20+ PNGs in named subdirs" — much closer to what the deliverable contract describes.

---

## Out of scope for this session

This diagnostic is a finding doc, not an implementation. the Developer or User picked **A + B + D for this cut** (the structure gate + template emitter + manifest update). The figures fixes above belong to a separate session — flagged for the next round so the W9 firebreak ships clean without scope creep.

— Opus
