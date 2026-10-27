# HTML readers: which tool builds which page

The bundle ships several HTML templates. A template is an empty page with a placeholder; its
builder fills it with data. Open the built output, never the raw template. Each page has its own
builder; there is no single `render-widgets` command for them (that command is described in
[widget deliverables](WIDGET_DELIVERABLES.md)).

## Pages and builders

| Template | Builder | What it writes |
|---|---|---|
| `bundle_support/deliverable_menu_widget.html` | `tools/build_deliverable_menu_widget.py` (`--out`, or `--stdout`/`--json`) | One HTML file. Already filled: a snapshot of the command and deliverable catalog. Commands shown on the page do not run. |
| `deliverable_tools/related_view.html` | `deliverable_tools/build_related.py config output` | `index.html`, `view.json`, partitions and audits. Fills `__DATA__`. |
| `deliverable_tools/strain_portfolio/portfolio_template.html` | `deliverable_tools/strain_portfolio/build_portfolio.py --config --output [--source-root]` | `START_HERE.html`, `portfolio.json`, partitions and `BUILD_RECEIPT.json`. Fills `__PORTFOLIO_DATA__`. |
| `tools/explorer_template.html` | `tools/build_domain_explorer.py --database --reader --output --population --expected-census [--pilot] [--template]` | `index.html`, `data.json`, `SOURCE_MANIFEST.json`. Fills `__DATA__`. |
| `tools/next_evidence_actions.html` | `tools/cohort_next_evidence_actions.py --root --manifest --manifest-pin [--port] [--audit]` | Nothing on disk: a local web server. |
| `tools/reaction_gap_board.html` | `tools/reaction_gap_board.py --source --manifest-sha256 --contract --output [--pilot] [--strain]` | `index.html`, `board_data.json`, `BUILD_RECEIPT.json`. Fills `/*DATA*/`. |
| `tools/pcoa_bgc_explorer_template.html` | `tools/pcoa_bgc_explorer.py` | `index.html` plus `data/*.js`, loaded by script tags so it works from disk. |
| `tools/cohort_tailoring/atlas_template.html` | `tools/cohort_tailoring/build_atlas.py` | `START_HERE.html` and `ATLAS_DATA.json`. |
| `mamey/data/siderophore_atlas.html` | `tools/render_siderophore_atlas.py` | One HTML file filled from a pinned atlas JSON. Search and filters; no export. |
| `mamey/enzyme_neighborhoods.html` | `mamey/cohort_enzyme_neighborhoods.py` | A standalone explorer. Fills `__VIEW_DATA__`. Up to three loci side by side, raw evidence drawers. |
| `mamey/evidence_disagreements.html` | `mamey/evidence_disagreements.py` | Nothing on disk: served on loopback with `/api/*` routes. |

The filled pages load no external scripts or styles. Two pages need their own local server:
the next-evidence page (`/api/meta`, `/api/queue`, `/api/evidence`) and the evidence
disagreements page. Opening either through `file://` shows nothing useful.

Several builders cover the private `frozen45` cohort: the related view, the strain portfolio and
the reaction-gap board. Keep their output inside the approved handoff.

All of these pages show existing annotations. None of them establishes orthology, a product,
pathway completeness or activity. Missing, unbound, not-run and parse-failed states are not
biological zero. Keep the full `strain / full node-or-contig / region / BGC alias` in any
locus-specific handoff.

## Reading the pages

**Domain explorer.** The two annotation channels, `aSDomain` and `PFAM_domain`, stay separate.
Proteins are de-duplicated by strain, contig, tag, coordinates, strand and protein hash. Patterns
are within one protein, not gene order or pathway architecture. By default the table shows
patterns found in at least two strains, 30 per page. Picking one strain reveals singletons.
`observed-domain-counts.json` exports every filtered pattern, not just the visible page. Locus
memberships overlap and class labels are multi-label, so do not add class strata together.

The builder checks the database's sibling `RELEASE_MANIFEST.json`, the reader hash and its
admission gate. `--expected-census` is the exact `binding.census_sha256`, not a record count.
`--population` is a display label, not a roster selector. Unordered patterns require two distinct
labels and discard repeats; ordered patterns retain repeats but hold order when intervals overlap
or the strand is unbound. Exact coordinate/label duplicates collapse first. Browser exports carry
the current counts and filters, not the full raw evidence package; retain their own hashes.

**Domain explorer pilot.** `--pilot` takes the first locus, in identity order, from each of up to
five strains. Some counts and held records still come from the whole database, so pilot output
is not a redacted handoff. The label gives the real count, such as "3-strain pilot subset".

**Reaction-gap board.** It shows the first eligible saved rank per strain, at most 45 pairs. A
displayed pair is a routing suggestion, not an accepted partner or mechanism.

**Siderophore atlas.** Frozen population, current entries and displayed records are separate
counts. Its "negative controls" are selected source states, not biological absence. Links to
`GUIDE.pdf`, `GUIDE.docx` and `FIRST_FIVE_AND_NEGATIVE_AUDIT.json` work only if you supply those
files. Citation links leave the local page.

**Enzyme neighborhoods.** The builder selects up to five no-call controls, not always five. The
page text says flanks are 10 kb; check the real `flank_bp` in the source manifest. Missing linked
domains are not domain absence. See the [enzyme builder contract](ENZYME_NEIGHBORHOODS.md).

**Evidence disagreements.** Copying the HTML alone does not make the evidence portable. Export a
bounded audit only through its CLI. A page error is a hold, not an empty result. See
[candidate service contract](EVIDENCE_DISAGREEMENTS_CANDIDATE.md).

**PCoA explorer.** `--mibig-dmnd` runs DIAMOND, which is computation. Outlier thresholds and
visual isolation are for prioritizing, not proof of novelty.

**Annotation atlas.** `--limit` and `--offset` slice the output after the full build, so they do
not reduce reading or memory use. Full-population counts can sit beside pilot records; check the
scope fields before comparing numbers. A 120-second SQLite progress handler limits part of the
database work, not the whole build. Its current50 mapping checks the exact profile, not section completion.

## Output folders and recovery

Most builders write files one after another with no rollback. A failure can leave a partial
folder. Keep it, find the cause and build into a new folder. Do not delete source evidence.

| Builder | Existing output |
|---|---|
| Deliverable menu | Directly overwrites `--out` and creates parent folders; no paired completion receipt is written. The default path is relative to the current folder; `--root` picks the bundle to read, not the output folder. |
| Related view | Resumes only with an identical `RESUME_BINDING.json`. If `SELF_AUDIT.json` exists, it refuses with `SEALED_OUTPUT_USE_NEW_ROOT`. Cached partitions also need matching checksum files. |
| Strain portfolio | Existing files must be byte-identical; otherwise `OUTPUT_CONFLICT_USE_NEW_ROOT`. Source files inside the output folder are refused. |
| Domain explorer | A non-empty folder must have a matching `SOURCE_MANIFEST.json` and data/HTML hashes; then it returns the saved data without rebuilding. With `--template`, exactly one `__DATA__` placeholder is required; otherwise the build stops with `TEMPLATE_PLACEHOLDER_HOLD`. |
| Next-evidence server | Binds `127.0.0.1`, default port 8768, GET only. If a source changes after start, it holds until restarted. `--audit` checks sources and prints metadata. A page can return HTTP 400 with `status: HELD`; that is not an empty result. The manifest can be outside `--root`, and audit mode still imports the pinned reader code. |
| Reaction-gap board | Needs a new or empty folder; a non-empty one is refused. |
| PCoA explorer | Needs a new or empty folder and at least one matching kit TSV. Its `build_receipt` records arguments, not file hashes. |
| Annotation atlas | Output must stay inside the configured root; existing files must match exactly. |
| Siderophore atlas | Checks the atlas file SHA-256 and refuses an existing output. It prints hashes to stdout but saves no receipt, so keep them. |

Builders import Python readers from the selected bundle or source. A pinned hash fixes which
bytes run; it does not make running them harmless. Review the inputs before a build, and keep
templates separate from built output.

See [artifact and menu limits](ARTIFACT_MAP_LIMITS.md) for which registered outputs are
available.
