# Strain slides: one deck per strain, complete inventory, selected region slides

`tools/strain_slides.py` builds a slide deck for one strain from its sealed Mamey package and whatever other evidence you
hold for it. Every antiSMASH region retains an inventory row, and a second file lists every gene of every region. Dedicated region slides apply the documented omission rule below.

## Request this builder by name

Ask for the **Sapote-Mamey Strain slides builder** (`tools/strain_slides.py`):

> Use the Strain slides builder for [strain]. Use the validated package at [path] and the sources JSON at [path]. Write the main strain deck, complete region-gene-table companion, assets and build receipt under [output folder] with a fresh tag. Report missing channels, omitted region slides and the limits of fit checks. Preserve full locus identities.

The gene-table companion is a separate PowerPoint produced by the same build, not a second builder. The tag is a filename label: `--tag v2n` alone does not enable new code or assets.

### Version boundary: .447 and the v2n example

This guide describes the shipped .447 tool. The October 4 v2n example used .447 plus candidate .448 changes for a MIBiG reference-structure gallery and a caption explaining the yellow reference-match band. Those changes are not in the .447 baseline. To reproduce that style, bind the reviewed patched builder and compatible reference-structure assets explicitly. Request the gallery as reference chemistry; it does not establish production by the strain. The .448 patch card is an implementation/review record, not release approval.

## Quick start
```bash
python tools/strain_slides.py template > XS-001_sources.json     # fill in the paths you have
python tools/strain_slides.py build --sources XS-001_sources.json --out decks/ --tag v1
```
From this selected bundle root, in the compatible activated environment, install the optional dependencies with `python -m pip install '.[slides]'`. Run the tool by its bundle path; no `strain-slides` console command is registered. See [installation](INSTALL.md) for core setup. These are source-checked examples, not a claim that your input was built or reviewed.

## The sources file
The sources file names the input channels. Supply absolute paths, including paths inside nested figure/tree entries and BLASTp glob patterns. The .447 resolver handles existing top-level string paths relative to the sources file's folder; it does not recursively resolve nested lists/dictionaries. BLASTp patterns expand through the supplied glob list. Do not depend on the shell's working directory for nested paths.

| Key | What it is | Needed |
|---|---|---|
| `strain`, `package` | the strain ID and its sealed Mamey package folder | yes |
| `antismash_zip`, `mibig_gbk_dir` | the strain's antiSMASH ZIP and a folder of MIBiG GenBank files, for drawing gap-rescue maps | for maps |
| `gap_rescue_dir` | a gap-rescue folder: `SUMMARY.tsv`, one folder per run, and the adjudicator's `<run>_ADJUDICATION.tsv` files; an adjudication file's verdicts replace the run's own | no |
| `rggmci_scorecard_tsv` | the RG-GMCI pair scorecard (`strain`, `pair`, `layers_verdict`, `relative_source`, `relative_assembly`, `locus_gap_genes`) | no |
| `pfam_names_tsv` | `accession<TAB>name<TAB>description` for Pfam, so partner-contig genes carry names rather than PF numbers (the `NAME`/`ACC` lines of a local `Pfam-A.hmm`) | no |
| `gecco_dir` | GECCO output for the strain: `*.genes.tsv`, `*.features.tsv`, `*.clusters.tsv` | no |
| `pcoa_kit`, `pcoa_drop_origins` | Existing protein PCoA kit directory and optional origins to omit; the renderer consumes supplied panels/data rather than running a new comparison | no |
| `bigscape_region_tsv`, `bigscape_figure` | a per-region BiG-SCAPE family table and an overview figure | no |
| `rescue_verdicts_tsv` | one ruling per rescue link (HOLDS / TWO_SIMILAR_LOCI / REJECT / UNRESOLVED), with `strain`, `core identity`, `partner contig`, `verdict`, `rule` and optionally `partner region`; a link must appear under each region that should show it | no |
| `blastp_csv_globs` | stored BLASTp tables (`gene`, `hit_rank`, `subject_organism`, `pct_identity`) | no |
| `metadata`, `nearest`, `trees` | isolation as recorded, nearest public genomes, approved tree panels | no |
| `family_figures`, `extra_figures`, `pointers` | figures for one region, figures for the strain, and where other files live | no |

The package folder must contain `<strain>_2_inventory.csv` and `<strain>_gene_by_gene_all_bgcs.csv`; the tool reads them directly. Confirm that `strain` matches those filenames and source identities. Package validation is a prerequisite to your workflow: this builder does not itself run the package validator.

Keep absent channels explicit. Blank gene-table cells mean no record in that source, not a tested negative. A missing or malformed required file is an input failure, not biological absence.

Reconcile the inventory with the source gene roster before claiming complete coverage. Duplicate inventory `BGC_ID` rows collapse to the last row. The companion iterates inventory IDs only: an inventory region with no matching gene rows produces no gene-table page, while gene rows whose `bgc_id` is absent from the inventory are not rendered. “Complete” therefore means the admitted inventory and matching supplied gene rows were independently reconciled; the builder does not perform that completeness check. Keep full `strain / full node-or-contig / region / BGC alias` and per-region expected/observed gene counts in that reconciliation.

Some optional omissions do not fail the build. Missing tree/family/extra image files are skipped, unmatched BLASTp globs yield no hits, and unreadable stored BLASTp CSVs can be skipped. The stored-hit merge keeps the first rank-1 row for a gene in supplied-glob order and reverse filename order, except that a later organism-bearing row can replace one without an organism; it does not compare percent identities or establish the latest search. Supply a reviewed nonoverlapping result roster and compare requested versus included channels rather than interpreting blanks as absence.

## What the deck shows
1. **Overview, trees, landscape.** Only the tree panels listed are shown; the tool never builds a tree.
2. **Region tables.** Every region in one row: type, contig edge, KnownClusterBlast, gap rescue, RG-GMCI, BiG-SCAPE, GECCO.
3. **Dedicated slides for selected regions**, strongest evidence first. Ectoine-only and NAPAA-only regions (including mixtures of just those labels), and terpene-only regions whose best KnownClusterBlast reference label contains geosmin, are omitted from dedicated slides unless the tool retains qualifying split-link evidence: an accepted RG-GMCI signal or a SUPPORTED gap-rescue find on a different contig. This is a display-selection rule using source labels, not a compound assignment. Omitted regions retain inventory rows and complete gene-table coverage; the build receipt records `no_region_slide` reasons.
   - **The map** is the gap-rescue map from `tools/gap_directed_rescue.py`, its two rows lined up on the majority of matched genes. Each contig is turned by its strand evidence (most matched genes on the strand opposite their reference genes means reversed), and the contigs run left to right in the order their matches fall on the reference. The tool saves the renderer's own record of the contigs' order and which it drew reversed (`map_layout.json`).
   - **The gene strip** below follows that record, so the two pictures run the same way. Genes matched to the MIBiG reference sit in a gold band. Bars above the genes are GECCO's per-gene probability (dashed line at 0.8). Core genes, matched genes, and genes GECCO scores 0.8 or more carry their domain name, thinned so neighbouring labels
     never overlap (matched genes first). A panel where GECCO scores every gene below 0.1 says so in its bar area. GECCO calls
     few saccharide-only regions in any setting (32 of 731 in the 43 decks; looser domain filters did not change this on
     the strain where it was tested), so the region's GECCO line says a low score there is not evidence against it.
   - **Partner contigs.** For a gap rescue, the strip draws every partner contig the map drew that holds a find the
     partner checks rate SUPPORTED, with "//" between contigs, in the map's left-to-right order (the core is not always
     first). Each partner is cut to its found genes ± 2.5 kb
     and has its own GECCO bars and orientation. A paralog-family or single-gene find beside a supported one on
     the same contig is kept with it; a contig with no supported find is not drawn, on the map or the strip.
     At most two partner panels are drawn, most SUPPORTED finds first; the rest are counted under the strip. Only found
     genes are labelled: by the reference gene name, or the found gene's first Pfam name + "-like" when the reference
     names it only by an accession. A bare accession is never printed, on the strip or in the text.
   - **When a partner holds more of the reference.** If a partner region holds more found reference genes than this
     region (at least 3), the slide says so first ("More of the reference lies elsewhere") and points to that region's
     slide; its strip panel is marked "more reference genes" and this region is drawn as "this region", not "core".
   - **Split-cluster signal.** A region linked by RG-GMCI (HIGH or MODERATE), or holding a SUPPORTED gap-rescue find, is
     named with two layers: per-gene KnownClusterBlast (both regions hit mostly different genes of one MIBiG cluster in
     both top threes) and the RG-GMCI scorecard's intact-relative position (`rggmci_scorecard_tsv`: do the two loci lie
     together in the best public relative). It is shown when position is CONSISTENT, or when KCB is complementary and
     position does not contradict; "Two layers agree" or "One layer; a candidate". Position APART_CLOSE or CONFLICT sets
     it aside. A draft or distant relative (APART_WEAK) or none (NOT_READ) cannot decide. The two-proof check's second
     proof is a shared KS clade, which a cluster without a KS can never pass, so these layers are printed beside it.
   - **Assembled across contigs.** The reference genes found, grouped by step (core, halogenation, glycosylation,
     methylation, sugar supply, regulation, transport), each with its gene, identity and verdict mark. A step comes from the
     reference's product line, or else the found gene's Pfam names. When a gene's best KnownClusterBlast match is another
     cluster and closer than the map's reference, it is given in brackets. Reference genes named only by accession take the
     MIBiG file's short product name (for example a gene called LooH).
   - **The BGC in the protein PCoA** sits on the region slide, under the text: the two sets holding most of its
     proteins, with a short legend. The text flows on to a "continued" slide when it does not fit beside it. When the
     BGC is in more than two sets, a full PCoA slide follows: every set where this BGC's proteins have a point, most
     first, up to six panels, including CARD resistance-gene families when the kit has
     them (`RES_SETS.tsv`). The BGC's proteins, and its SUPPORTED partner-contig genes, are large stars labelled by locus
     tag and filled by identity to their best reference/MIBiG match; the strain's other proteins are pale red.
   - **The evidence lines** name each channel separately. The gap-rescue partners are drawn on the map. An RG-GMCI link is not drawn; its line gives the two-proof verdict and how many references complement each other. A HIGH link that the two-proof check rates WEAK is called "two similar loci, not one split cluster", and it does not raise the region's rank.
4. **GECCO-only candidates.** These are GECCO clusters that overlap no antiSMASH region, matched on `NODE_n_length_L` because GECCO rewrites contig names. A gene with a core enzyme domain is red.
5. **Region-gene tables** (a separate file). Every supplied gene row for each inventory region, in pages of up to 20 genes. Columns include amino-acid length, inferred role, domains, description/smCOG, GECCO probability, gap-rescue MIBiG match and stored BLASTp best hit. The .447 display keeps at most three unique domain names, ordered from the supplied domain table by E-value, and truncates some descriptions. It is a reading companion, not a lossless export of all annotations. GECCO-only clusters outside the antiSMASH inventory do not gain rows in this companion; keep their underlying GECCO tables separately.

Until a rescue verdict table is given, every region slide says "review draft: links not yet adjudicated" above its text. With a table, a region slide says "review draft: n of m links not settled" while any shown split partner lacks a HOLDS, TWO_SIMILAR_LOCI or REJECT ruling. Settled rulings are listed first. An UNRESOLVED ruling's rule is shown as the next check.

**Text fit.** A region slide's text is measured in Calibri widths (Carlito, its metric twin) and set at 9 pt, shrinking
to 7.5 pt; what still does not fit moves to a "continued" slide right after it. Slide numbers in the region table are
counted after the build, so they include these slides. To check a built deck:
```bash
python tools/strain_slides.py audit-fit \
  "/absolute/decks/XS-001_strain_slides_v1_<date>.pptx" \
  "/absolute/decks/XS-001_gene_tables_v1_<date>.pptx"
```

Replace `<date>` and both paths with the actual files. The command accepts one or more deck paths; a literal `...` is treated as another filename, not omitted arguments. It reports estimated text-box overflow/overlap and exits 1 if any examined deck has such problems. It only examines shapes with nonempty text frames; table-cell text is not included, so a zero-problem result does not establish gene-table readability.

## Supplied locus-comparison panels: verify input coverage separately

A separately supplied locus-comparison panel can render correctly while omitting genes or saved similarities. A graphics receipt verifies the admitted manifest, not its completeness against antiSMASH or another source. The .448 locus renderer is a separate integration candidate; it is not part of the shipped .447 builder described above.

Before accepting a comparison panel, reconcile:

- The full selected region/contig gene roster against the adapter manifest and actual drawn arrows. Record every crop and omitted gene with its reason.
- Saved matched query-gene IDs against admitted ribbon endpoints. Partner classification such as `SUPPORTED` is distinct from similarity-display coverage; a classification filter can hide real recorded matches.
- The exact comparison stream and reference record/version. KnownClusterBlast and gap-rescue DIAMOND identities or subject mappings are separate results; do not merge or relabel them silently.
- Source-observed assembly markers against the adapter fields. The renderer can show contig ends and missing-stop asterisks only when `sequence_length` and `missing_stop_codon` are supplied; lack of a marker is not a completeness observation.

Keep expected, selected and drawn counts and identities in the external build record. Compare matched genes, not only total ribbon counts. A correctly drawn cropped/filtered panel needs an explicit scope label; neither more similarities nor successful rendering promotes a product or physical-linkage claim. Cropping around admitted hits must not silently exclude a long CDS that crosses the crop boundary.

## Outputs and completion checks

For `strain=XS-001`, tag `v1`, and the build's local date, expect:

- `XS-001_strain_slides_v1_<date>.pptx`: main deck.
- `XS-001_gene_tables_v1_<date>.pptx`: region-gene companion.
- `XS-001_strain_slides_v1_<date>_RECEIPT.json`: top-level string source values, deck/region counts, region order and dedicated-slide omission reasons. It does not include the sources JSON hash, nested metadata/figure lists, BLASTp glob lists, input/output hashes or a full missing-channel roster.
- `XS-001_v1_assets/`: supporting maps and rendered assets.

The builder does not export PDFs. PDF conversion is a separate step. A receipt records the build; it is not scientific or visual acceptance. Inspect both decks as rendered pages before claiming visual QA. `audit-fit` estimates text-box fit and does not establish table-cell readability, complete source evidence or rendered-page quality.

The .447 overwrite check protects the main deck filename. Use a new output folder and tag when either companion or receipt already exists; do not assume every output has an independent overwrite guard.

If a build fails, preserve its log and partial outputs. The main deck is saved before the gene companion and receipt, so a main PPTX alone does not establish completion. Multiple files supplied to one `--sources` call build sequentially; a later failure leaves earlier builds in place and prevents remaining builds. Reconcile each requested strain with its own two PPTX files, assets and receipt.

Check required package tables, source paths and optional dependencies, then retry with a fresh tag/output folder. Existing map PNG plus `map_layout.json` in the assets tree are reused without checking the current source hashes; changing source files while reusing assets can retain a stale map. Missing map inputs, a map source mismatch or caught redraw errors can leave a successful deck with no map; retain stderr and report the missing panel. For wrong strain/contig joins, hold the affected attribution and correct the source binding before rebuilding.

Keep an external hash-bound build record containing the sources JSON, all selected nested/glob inputs, package validation receipt, builder identity and every output. The receipt's `adjudicated` Boolean only tests whether the sources field is nonempty; a nonexistent verdict path can still set it true. Reconcile the loaded ruling roster and the actual shown link dispositions before treating a deck as adjudicated.

## Protein PCoA panels
`tools/strain_slides_pcoa.py --kit <kit> --strain <ID> --out <folder> --groups "a:label A,b:label B"` draws two six-panel
figures from a kit made by `tools/protein_pcoa_ordinate.py`.
- **Layers:** the strain on top, in three identity tiers; then each isolate group in the order given; then MIBiG; then reference genomes.
- **Using them in a deck:** list the PNGs under `extra_figures`.
- **Per BGC:** `strain_slides_pcoa.bgc_figure(kit, strain, locus_tags, out, cache)` draws one BGC's proteins as stars in
  every set that holds them; `kit_sets(kit)` lists a kit's ordinated sets and reads CARD family names.

## Rules
- Each region is shown as `strain / full contig / region / BGC alias`, copied from the package inventory.
- The existing main-deck filename is refused. The companion deck, receipt and assets do not each have an independent overwrite guard; use a fresh output directory and tag, including after a failed build.
- Similarity is not identity, capacity is not production, and a family is shared architecture, not a compound.
