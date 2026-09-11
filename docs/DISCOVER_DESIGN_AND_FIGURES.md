# `discover` design + the Sapote-Mamey figure suite (catalogue)

Two things the user asked for, documented together because `discover` *routes to* the figure verbs.

---

## Part 1 — `discover` design

### The gap it fills
Mamey already has three situational-awareness verbs, each scoped to a different unit:

| verb | unit of attention | question answered |
|---|---|---|
| `doctor` | the **environment** | "are my deps/paths ready to run?" |
| `inspect` | one **input ZIP** | "what's in this antiSMASH bundle before I run it?" |
| `explain` | one **sealed package** | "what did this run find?" |
| **`discover`** *(new)* | a **workspace / cohort** | "what's here, how complete, and what do I run next?" |

Nothing previously answered the *workspace* question. In a real deliverables tree (dozens of
sealed packages across `mamey_packages/`, `runs_*/`, per-cohort folders, plus patch/cut staging)
the human cost is orientation, not computation. `discover` is that orientation, encoded once next
to the output contract it reads.

### Contract it keys on (why it lives in-tree, not as a script)
`discover` reads only Mamey's own emitted artifacts:
- **package identity** — `manifest_short.json` (`strain_id`, `mamey_version`, `release`,
  `status`, `assembly_tier`, `raw_bgcs`, `corrected_bgcs`); falls back to `manifest.json`.
- **gate** — `gate_validation.json.status`; **mode** — `gold_mode_receipt.json.mode`.
- **coverage flags (file-presence)** — `gold_figures/` or `*_8a_fig_landscape.png` (figures),
  `modeb_verdicts.csv` (Mode-B), `bgc_blastp_panel/` (BLASTp ingested),
  `*_5b_manual_blastp_worklist.csv` (BLASTp pending → ⧗), `*_compiled_report.md` (report).

Because those names are the package contract, the "what's next" logic stays correct as the
contract changes — the same rationale that keeps `explain` in-tree.

### Output modes
- default: a human table + workspace context + ranked next-actions.
- `--json`: the same as a dict (for tooling / Lab Quest / dashboards).
- `--emit-md PATH`: also write the report to a file (a `DISCOVERY.md` you can commit).
- `--depth N`: bound recursion (default 6); a package dir stops descent (its subdirs aren't packages).

### Next-action ranker
Pure function of the scanned state — `_suggest(packages, context)`:
`validate` (non-passing gates) → `ingest-blastp` (worklist-only) → `render-all-figures` (no figures)
→ `mode-b` (no verdicts) → `cohort-figures`/`cohort` (≥2 packages, no cohort deck) → a note on
pending patch/cut folders → `re-run` (engine drift: packages older than the newest engine seen /
`--current`). Every line names a real subcommand, so `discover` is a launcher, not a lecture.

---

## Part 2 — the figure suite (the "figure-making process," documented)

Sapote-Mamey's figure system is already extensive; `discover` surfaces *coverage* and points at
the right verb. This is the catalogue so the process is legible in-code.

### Figure verbs (CLI)
| command | scope | emits |
|---|---|---|
| *(gold run, automatic)* | per strain | the numbered `_8*` figure pack into `gold_figures/` at seal |
| `render-figures` | one package | (re)render the per-strain figure pack |
| `render-all-figures` | one package | the full per-strain set incl. extended panels |
| `cohort-figures` | many packages | cross-strain cohort panels (class heatmap, landscape, DAPR) |
| `cohort` | many packages | the cohort deliverable (figures + synthesis) |
| `figures` | package/cohort | **publication** figures: `diagram \| atlas \| ani \| gcf-network \| clinker` |

### Per-strain pack (emitted at gold seal → `gold_figures/`, mirrored as `_8a…_8n`)
`8a` landscape · `8b` composition · `8c` DAPR scatter · `8d` AB-ranked · `8e` AF-ranked ·
`8f` funnel · `8g` AB/AF panels + class distribution · `8h` CCTT map · `8i` length histogram ·
`8j` edge composition · `8k` novelty-ranked · `8l` KCB anchors · `8m` genome atlas ·
`8n` RG-GMCI rescue. Each ships with its `*_data.csv` (the figure's source table — figures are
reproducible from data, never hand-drawn).

### Module map (`mamey/*figure*`)
| module | role |
|---|---|
| `figure_policy.py` | **style/appearance policy** — the single place that governs palette, sizing, claim-safe labelling. Start here to change house style. |
| `bgc_figures.py` | per-BGC / per-strain figure primitives |
| `mamey_native_figures.py`, `figures_sapote.py`, `figures_extra.py`, `figures_split.py` | the per-strain pack renderers + variants |
| `render_all_figures.py` | orchestrates the full per-strain set |
| `cohort_figures.py`, `cohort_figures_extended.py` | cross-strain cohort panels |
| `collection_figures.py`, `cross_strain_figures.py` | collection/cross-strain threads |
| `bigscape_figures.py` | GCF-network (BiG-SCAPE) figures |
| `domain_figures.py` | domain-level (Mode-B) figures |
| `master_figure_atlas.py` | the master atlas assembly |
| `boundary_palette.py` | boundary/edge colour conventions |
| `figures_smoke.py` | smoke-mode minimal figures |

### The process (how a figure is made, for contributors)
1. A scan/scoring step writes a **data table** (`*_data.csv`) — the figure's ground truth.
2. A renderer in the module map reads that table and draws with **matplotlib**, applying
   `figure_policy` for style + claim-safe labels (AF/AB shown as *routing priors*, KCB as
   *similarity*, never as activity/identity).
3. The figure + its `_data.csv` are written to `gold_figures/` (per-strain) or the cohort output
   dir. Nothing is drawn from memory; re-running reproduces byte-comparable data.
4. `discover` reports the figure as present (✓) once `gold_figures/`/`*_8a_fig_landscape.png`
   exists, and routes to `cohort-figures` when ≥2 packages lack a cohort deck.

**To extend the suite:** add a renderer that consumes an existing `*_data.csv` (or emit a new data
table first), wire it into `render_all_figures.py` (per-strain) or `cohort_figures*` (cohort),
route its appearance through `figure_policy`, and — if it becomes a required output — add its
suffix to the package contract so `discover`/`validate` can see it.
