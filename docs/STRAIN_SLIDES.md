# Make slides from one strain's package

Make a PowerPoint overview and a separate gene-table deck from a validated
package. You need the installed bundle and the package's inventory and gene tables.
Trees, comparison results and other panels are optional.

## Build the two decks

From the program folder, install the slide dependencies first:

```bash
python -m pip install '.[slides]'
python tools/strain_slides.py template > AS-40_sources.json
```

Open `AS-40_sources.json`. Set `strain` to your run label and `package` to the
extracted package folder. For a sources file in the program folder, the example
values are `EXAMPLE` and `runs/EXAMPLE/package`. Leave unavailable inputs empty.
The strain must match the names of the inventory and gene-table files.

Choose a new output folder, then build:

```bash
python tools/strain_slides.py build --sources AS-40_sources.json --out decks/EXAMPLE/
```

The terminal reports the main-deck slide count, region count and gene-table slide
count. The output folder contains two PPTX files, a `_RECEIPT.json` file and an
assets folder. Filenames include the strain, the default `v2` tag and the build
date. `--tag` changes a filename label; use it only when you need another label.

Open **both** decks and inspect their pages. Then check estimated text-box fit:

```bash
python tools/strain_slides.py audit-fit decks/EXAMPLE/*.pptx
```

The check reports overflow and overlap, returning exit 1 for problems. It skips
table-cell text, so inspect the gene tables even when it reports zero problems.
The builder makes PowerPoint files; export PDF from your presentation application
if you need it.

## What to expect

Every antiSMASH inventory region has a row in the overview and its supplied genes
appear in the gene-table deck. Dedicated region slides use a selection rule:
ectoine-only, NAPAA-only, hydrogen-cyanide-only and geosmin-labeled terpene-only
regions can be omitted unless qualifying split-link evidence keeps them. Mixtures
of just the first three labels use the same rule. The receipt lists the omitted
region slides and reasons. Keep each identity as
**strain / full contig / region / BGC alias**.

The gene-table deck uses up to 20 genes per page. It shortens descriptions and
shows at most three unique domain names, ordered by E-value; use the CSV for the
complete annotations. GECCO-only clusters outside the antiSMASH inventory have
separate main-deck slides and keep their own underlying gene tables.

Blank optional inputs produce a simpler deck. The builder shows the tree panels
you supply and reads existing comparison results. 
A region can say “review draft: links not yet adjudicated” when no rescue verdict
has been supplied. Read that as a request to review the displayed links.

## Add optional sources

Use full paths for entries inside figure/tree lists and for BLASTp glob patterns;
only existing top-level string paths are resolved relative to the sources file.
The [installation guide](INSTALL.md) covers the core environment.

| Sources-file field | Add it when you have |
|---|---|
| `antismash_zip`, `mibig_gbk_dir` | The matching antiSMASH ZIP and MIBiG GenBank files for gap-rescue maps |
| `gap_rescue_dir` | Gap-rescue tables and their reviewed verdict files |
| `rggmci_scorecard_tsv` | A saved pair scorecard, with its recorded rule policy |
| `pfam_names_tsv` | A Pfam accession/name/description table for readable domain labels |
| `gecco_dir` | The strain's GECCO genes, features and clusters tables |
| `bigscape_region_tsv`, `bigscape_figure` | A per-region family table and overview panel |
| `pcoa_kit`, `pcoa_drop_origins` | An existing protein PCoA kit and any origins to omit |
| `blastp_csv_globs` | Saved BLASTp tables with gene, hit rank, organism and identity fields |
| `rescue_verdicts_tsv` | Reviewed link rulings: HOLDS, TWO_SIMILAR_LOCI, REJECT or UNRESOLVED |
| `metadata`, `nearest`, `trees` | Recorded sample metadata, nearest-genome results and tree panels |
| `family_figures`, `extra_figures`, `pointers` | Existing panels and links to other files |

A rescue ruling needs `strain`, `core identity`, `partner contig`, `verdict` and
`rule`; add `partner region` when known. List a link for each region that should
show it. Check the loaded rulings: the receipt's `adjudicated` field only checks
whether a verdict path was entered, even if that file does not exist.

Reference-structure galleries read `chemical_structures_json` or the assets
folder's `chemical_structures/STRUCTURE_ASSETS.json`. Use compatible reference
assets and check the receipt's gallery counts against the displayed structures.

<details>
<summary>Read maps and comparison panels</summary>

Gap-rescue maps use the bundle's renderer and its saved `map_layout.json`.
Gene strips follow that recorded orientation. The gold band marks genes matched
to the reference. GECCO bars show per-gene probability with a line at 0.8.

Partner panels show at most two contigs with SUPPORTED finds, cropped around the
finds with 2.5 kb of flanking sequence. Additional partners are counted below the
strip. Check saved matches and omitted genes when reviewing a cropped panel;
compare the full gene roster with the arrows and ribbon endpoints actually shown.
Keep KnownClusterBlast and gap-rescue DIAMOND matches identified separately.

Read the saved two-proof result under its `rule_policy` and
`second_proof_channel`. The `class_routed_v1` policy uses KS-clade evidence for
KS-bearing pairs and class-core completion for eligible non-KS pairs;
`ks_clade_v2` is the older selectable policy. Keep candidate links between
contigs separate from claims of a physically continuous locus.

Protein PCoA panels use an existing ordinated kit. The region slide shows the
sets holding the most of its proteins; additional panels can follow. Use
`tools/strain_slides_pcoa.py` with the kit and strain you selected, then add the
resulting PNGs under `extra_figures`.

</details>

## If a build is incomplete

Check for **both decks and the receipt**: the main deck is saved first, so it can
exist after a later step fails. Keep the log and partial outputs, fix the reported
input or dependency, and retry in a new output folder. The main deck has an
overwrite guard; companion files and assets do not each have one.

Use a new assets folder when source files change because existing map PNGs and
layout records can be reused without a source-hash check. Read stderr for omitted
or mismatched panels even after a successful build. Keep the sources JSON and
hashes of the package, selected inputs, builder and outputs beside the decks;
the built-in receipt does not include all of those hashes or nested source lists.

<a id="request-this-builder-by-name"></a>
<a id="quick-start"></a>
<a id="the-sources-file"></a>
<a id="what-the-deck-shows"></a>
<a id="supplied-locus-comparison-panels-verify-input-coverage-separately"></a>
<a id="outputs-and-completion-checks"></a>
<a id="protein-pcoa-panels"></a>
<a id="rules"></a>
