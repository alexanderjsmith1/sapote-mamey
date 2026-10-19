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

The scanner keys on specific filenames. Contract changes require corresponding source updates; discovery does not automatically track new filenames or verify their contents.

### Output modes
- default: a human table + workspace context + ranked next-actions.
- `--json`: the same as a dict (for tooling and dashboards).
- `--emit-md PATH`: also write the report to a file (a `DISCOVERY.md` you can commit).
- `--depth N`: bound recursion (default 6); a package dir stops descent (its subdirs aren't packages).

Optional governed discovery requires `--source-collection-registry`, its exact
`--expected-source-collection-registry-sha256`, and a logical `--source-root-id`.
Request `--emit-source-catalog-json` and `--emit-source-catalog-tsv` together. Both
catalog paths must be fresh, distinct, and free of symlink ancestors; choose new
names for each scan. The standalone `python -m mamey.workspace_source_discovery
scan` command uses the same fresh-pair policy and refuses an occupied pair before
scanning. This deliberately replaces the older behavior that overwrote catalog files.

The complete selected output roster is checked before discovery. Report/catalog
path collisions and a report that aliases the selected registry, including a
hardlink, are refused. `--emit-md` retains ordinary report replacement and requires
an existing parent. The report and both catalog formats are serialized first; an
existing report is staged and replaced only after both fresh catalog files succeed.
An ordinary publication failure preserves the previous report and attempts to
remove only files created by this invocation. Any failed or ownership-changed
cleanup is attached to the original error. An absent report is created exclusively
as the final fresh output.

Existing reports are replaced with a new file inode. Permission mode is copied;
ownership, ACLs and extended attributes are not explicitly copied. Other hardlinks
retain the previous file. Directory permissions govern replacement, which can
succeed where a direct write to the old report would fail. Confirm these file
metadata semantics before adopting this report replacement behavior.

The shared byte publisher also rejects parent traversal, symlink ancestors and
casefolded duplicate or ancestor output slots when no report replacement is
requested. Its callers must satisfy that roster policy. Tools that resolve their
output roots before publication retain their existing resolving contract.

An incomplete governed scan writes its diagnostic outputs and returns exit 3.
Only `PASS_COMPLETE` catalogs can pass report-source preflight. Output publication
errors fail without a success marker. Interruption can leave a partial set or a
staging file, and console failure after file commit does not undo committed files.
Retain the diagnostic and inspect the actual output roster before retrying with
fresh catalog names. Use one writer and stable input/output paths. The registry
alias guard is not a complete inventory of every source file in a workspace.

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
| `figures` | package/cohort | candidate figures: `diagram \| atlas \| ani \| gcf-network \| clinker` |

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
1. A scan/scoring step writes a **data table** (`*_data.csv`) — the figure's saved display inputs; source admission is separate.
2. A renderer in the module map reads that table and draws with **matplotlib**, applying
   `figure_policy` for style + claim-safe labels (AF/AB shown as *routing priors*, KCB as
   *similarity*, never as activity/identity).
3. The figure + its `_data.csv` are written to `gold_figures/` (per-strain) or the cohort output
   dir. Nothing is drawn from memory; reproducibility requires the exact input/code/config/runtime bindings; this catalog does not verify them.
4. `discover` reports the figure as present (✓) once `gold_figures/`/`*_8a_fig_landscape.png`
   exists, and routes to `cohort-figures` when ≥2 packages lack a cohort deck.

**To extend the suite:** add a renderer that consumes an existing `*_data.csv` (or emit a new data
table first), wire it into `render_all_figures.py` (per-strain) or `cohort_figures*` (cohort),
route its appearance through `figure_policy`, and — if it becomes a required output — add its
suffix to the package contract so `discover`/`validate` can see it.

## Current implementation and reader limits

`mamey/discover.py:32–110` identifies a package by either manifest filename, stops descending into that folder, and swallows JSON read/parse errors into an empty object. It chooses the first existing short/full manifest, not the first valid one: a malformed short manifest prevents fallback to a valid full manifest. Metadata and gate states are read rather than freshly validated. No package/source hash, sealing, exact locus or current50 verifier is run.

Capabilities are top-level filename/directory-presence flags. An empty `gold_figures` directory or `bgc_blastp_panel` name can mark a layer present. Figure counts inspect only a subset of PNG locations; Mode B counts physical verdict-file lines minus one, not verified cards or CSV records; BLASTp counts directory entries, not admitted queries. Existing SVGs, different figure directories or a full finished card can be invisible to these proxies. They are navigation hints, not evidence of completion, freshness, coverage, visual QA or scientific acceptance. Preserve strain / full node-or-contig / region / BGC alias in actual locus reports.

Version drift compares parsed package engine versions to `--current` or the newest discovered value; a stale flag is not authorization to rerun or mutate a sealed source. Suggestions are strings, not executed commands or complete invocations. `--emit-md` follows the staged replacement contract above and needs its parent to exist; the ordinary discovery report lacks a source/hash receipt. The optional source catalog separately requires an explicit registry hash and source-root ID; catalog inclusion still does not grant evidence authority.

The figure module map is a navigation list, not proof that every renderer imports one policy or uses the same palette/output format. Not all figures emit raw CSVs, and generated source tables can be aggregates or derived metrics. There is no universal automatic figure count or guarantee that every numbered panel exists after a run. Consult [the current catalog](FIGURE_CATALOG.md), [reproducibility limits](FIGURE_REPRODUCIBILITY.md), and [optional figure tool contracts](OPTIONAL_FIGURE_FACTORY_TOOLS.md).

`render-all-figures` validates a readable manifest and reports per-set `RAN`, `SKIPPED`, `ERRORED`, `UNKNOWN_SET` or `DRY_RUN`. Skipped sets can yield `PASS_WITH_SKIPS` and exit0; requesting no sets can yield PASS without rendering. Render execution, publication approval, biological validation and release approval are separate statuses. Gathering copies PNG/SVG files and labels current versus stale/untracked entries; its manifest hashes copies, not all original data/configs or source admission (`mamey/render_all_figures.py:113–230,536–623,630–739`). The command writes package subdirectories and a summary, so a “post-seal” name does not imply immutable read-only behavior. Use a separately authorized candidate or external route before any rendering. Record the actual requested/rendered/skipped set roster and partial outputs.
