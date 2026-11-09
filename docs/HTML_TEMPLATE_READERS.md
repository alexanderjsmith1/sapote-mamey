# HTML readers: which tool builds which page

The bundle ships several HTML templates. A template is an empty page with a placeholder. A
builder fills it with data. Open the built output, never the raw template. The deliverable menu is
the exception: the shipped `bundle_support/deliverable_menu_widget.html` is already a built page,
and its template lives inside `tools/build_deliverable_menu_widget.py`.

Each page has its own builder. The `render-widgets` command is a different tool: it reads a
sealed package ([widget deliverables](WIDGET_DELIVERABLES.md)). The builders below read inputs
you prepare. Run each from the bundle root. A builder prints its own usage with `--help`.

Only the deliverable menu and the PCoA explorer work from files you can make yourself (the PCoA
explorer takes the kit from `protein_pcoa_ordinate.py`; see
[locus and PCoA tools](LOCUS_AND_PCOA_TOOLS.md)). The others are cohort tools. They need prepared
inputs, and each is described in the notes below the table:

- a **config** or **selection** file: a JSON file that names the source files and pins each one by
  SHA-256;
- a **manifest pin** or **manifest SHA-256**: the SHA-256 of the source manifest, which the builder
  compares with the file on disk;
- a **reader** or **contract** file: the Python reader or section profile that the source database
  was built with, again checked by hash.

If you do not have these files, you cannot build those pages; ask whoever built the database.

## Pages and builders

| Template | Builder and required arguments | What you get |
|---|---|---|
| `bundle_support/deliverable_menu_widget.html` (a built page, not a template) | `tools/build_deliverable_menu_widget.py` with `--out <path>`, `--stdout` or `--json` | `--out` writes one filled HTML file to that path and prints the path. An existing file is refused with exit 2. Without `--out` the path is `bundle_support/deliverable_menu_widget.html`, which exists in the bundle, so the run is refused unless you add `--replace`; that flag is for a maintainer rewriting the shipped page. `--stdout` prints the HTML and writes no file. `--json` prints the JSON payload and writes no HTML. The page is a snapshot of the command and deliverable list; commands shown on it do not run. |
| `deliverable_tools/related_view.html` | `deliverable_tools/build_related.py <config> <output>` | `index.html`, `view.json`, partitions and audits. |
| `deliverable_tools/strain_portfolio/portfolio_template.html` | `deliverable_tools/strain_portfolio/build_portfolio.py --config --output` (optional `--source-root`) | `START_HERE.html`, `portfolio.json`, partitions and `BUILD_RECEIPT.json`. |
| `tools/explorer_template.html` | `tools/build_domain_explorer.py --database --reader --output --population --expected-census` (optional `--pilot`, `--template`) | `index.html`, `data.json`, `SOURCE_MANIFEST.json`. |
| `tools/next_evidence_actions.html` | `tools/cohort_next_evidence_actions.py --root --manifest --manifest-pin` (optional `--port`, `--audit`) | No files. It starts a local web server. |
| `tools/reaction_gap_board.html` | `tools/reaction_gap_board.py --source --manifest-sha256 --contract --output` (optional `--pilot`, `--strain`) | `index.html`, `board_data.json`, `BUILD_RECEIPT.json`. |
| `tools/pcoa_bgc_explorer_template.html` | `tools/pcoa_bgc_explorer.py --kit --regions --out` | `index.html` plus `data/*.js`. It works when opened from disk. |
| `tools/cohort_tailoring/atlas_template.html` | `tools/cohort_tailoring/build_atlas.py --config --output` (optional `--pilot`, `--offset`, `--limit`) | `START_HERE.html` and `ATLAS_DATA.json`. |
| `mamey/data/siderophore_atlas.html` | `tools/render_siderophore_atlas.py <atlas> --sha256 --output --permitted-root` | One HTML file built from a pinned atlas JSON. It has search and filters, and no export. |
| `mamey/enzyme_neighborhoods.html` | `tools/build_enzyme_neighborhoods.py --config --out` (optional `--pilot`) | A standalone explorer. It shows up to three loci side by side, with drawers for raw evidence. |
| `mamey/evidence_disagreements.html` | `tools/evidence_disagreements.py --selection` (optional `--port`, `--audit`) | No files. It serves pages on the local machine with `/api/*` routes. |

The filled pages load no external scripts or styles. Two pages need their own local server:
the next-evidence page (`/api/meta`, `/api/queue`, `/api/evidence`) and the evidence
disagreements page. Opening either through `file://` shows nothing useful.

Some builders read a private cohort (the related view, the strain portfolio and the reaction-gap
board). Do not share their output outside your team.

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

**Reaction-gap board.** It builds only for the frozen 45-strain database; any other population stops with an error. It shows the first eligible saved rank per strain, at most 45 pairs. A
displayed pair is a routing suggestion, not an accepted partner or mechanism.

**Siderophore atlas.** Frozen population, current entries and displayed records are separate
counts. Its "negative controls" are selected source states, not biological absence. Links to
`GUIDE.pdf`, `GUIDE.docx` and `FIRST_FIVE_AND_NEGATIVE_AUDIT.json` work only if you supply those
files. Citation links leave the local page.

**Enzyme neighborhoods.** The builder selects up to five no-call controls, not always five. The
page text says flanks are 10 kb. Read the real `flank_bp` in the source manifest. Missing linked
domains are not domain absence. See the [enzyme builder contract](ENZYME_NEIGHBORHOODS.md).

**Evidence disagreements.** Copying the HTML alone does not make the evidence portable. Export a
bounded audit only through its CLI. A page error is a hold, not an empty result. See
[candidate service contract](EVIDENCE_DISAGREEMENTS_CANDIDATE.md).

**PCoA explorer.** `--mibig-dmnd` runs DIAMOND, which is computation. Outlier thresholds and
visual isolation are for prioritizing, not proof of novelty.

**Annotation atlas.** `--limit` and `--offset` slice the output after the full build, so they do
not reduce reading or memory use. Full-population counts can sit beside pilot records; check the
scope fields before comparing numbers.

## Output folders and recovery

Most builders write files one after another with no rollback. A failure can leave a partial
folder. Keep it, find the cause and build into a new folder. Do not delete source evidence.
Builders refuse an existing folder unless the table says they can resume it.

| Builder | Existing output |
|---|---|
| Deliverable menu | Directly overwrites `--out` and creates parent folders; no paired completion receipt is written. The default path is relative to the current folder; `--root` picks the bundle to read, not the output folder. |
| Related view | Resumes only with an identical `RESUME_BINDING.json`. If `SELF_AUDIT.json` exists, use a new output folder. Cached partitions also need matching checksum files. |
| Strain portfolio | Existing files must be byte-identical; otherwise use a new folder. Source files inside the output folder are refused. |
| Domain explorer | A non-empty folder must have a matching `SOURCE_MANIFEST.json` and data/HTML hashes; then it returns the saved data without rebuilding. With `--template`, exactly one `__DATA__` placeholder is required; otherwise the build stops with a hold. |
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
