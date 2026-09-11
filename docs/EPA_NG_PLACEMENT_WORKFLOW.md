# EPA-ng 16S Placement — the formal Sapote-Mamey workflow (paper-ready)

**Lane:** Eggplant · **Engine:** sapote-mamey ≥ v9.7.411 (needs the EGGPLANT_411 patches) · **Status:** formal, end-to-end.
**Supersedes** the older `docs/PHYLO_PLACEMENT_WORKFLOW.md`, which referenced a producer (an older unpackaged producer script)
that was never packaged, leaving the ggtree renderer orphaned. This workflow is self-contained: every step
is a shipped tool.

> **Claim-safety (governing).** 16S rRNA is a phylogenetic **anchor / clade-neighbourhood** indicator, **not**
> a species assignment. A placement states the genus/clade neighbourhood a query falls into on a FIXED
> reference backbone, with a per-query **likelihood-weight ratio (LWR)** as confidence. No ANI/AAI, no
> bioactivity/structure claims; judgment deferred.

## When to use this
16S-only strains (no genome), or a fast neighbourhood read before a genome/MLSA tree. Queries are **placed**
on a fixed type-strain backbone; they never perturb its topology. For genome trees use `docs/GTOTREE_WORKFLOW.md`.

## The pipeline (one command per stage)

```
phylo_place.py all <ref_16S.fasta> --group <Genus> --query <queries.fasta> \
     --reference-metadata <ref_16S_meta.tsv> \
     --add-outgroup <Genus> --one-per-species --bootstrap 10 --outdir <run>/placement
     # build-ref (mafft → raxml-ng GTR+G, rooted on the registry outgroup) → EPA-ng place → gappa graft → report
     # driver interpreter: Tools/bin/python3 (Biopython); binaries: miniconda3/envs/placement/bin
     # → epa_result.jplace, epa_result.newick, <Genus>_placements.tsv, <Genus>_neighborhoods.tsv, refpkg/

phylo_postflight.py <run>/placement/epa_result.newick --outgroup <OutgroupGenus>   # P3 is placement-aware
tree_sanity_check.py <run>/placement/epa_result.newick --outgroup <OutgroupGenus>  # must PASS (outgroup-aware)

build_placement_ggtree_inputs.py --graft <run>/placement/epa_result.newick --group <Genus> \
     --neighbors <N> --host-table <paper strain table> --origin-table <isolation_source.tsv> \
     --ref-source-db <16S store with record(acc_base, isolation_source, host, country)> \
     --outgroup-substr <OutgroupGenus> --out-prefix <run>/ggtree/<Genus>
     # → <Genus>_pruned.nwk + <Genus>_ggtree_annotation.tsv (host+accession on queries; isolation-source on refs)
     # --ref-source-db has NO default and NO automatic discovery. Omit it and every reference tip is
     # NOT_REQUESTED and renders bare -- the line above promises isolation-source on refs, and only this
     # flag delivers it. The producer now says so on stderr; reference_source_status records it per tip.

GG_TITLE="..." GG_METHODS="<full methods paragraph>" \
Rscript ggtree_placement.R <run>/ggtree/<Genus>_pruned.nwk <run>/ggtree/<Genus>_ggtree_annotation.tsv \
     <run>/ggtree/<Genus>_fig noloc
     # → paper-ready PDF + PNG: queries red/bold (host + 16S accession), refs blue with an
     #   isolation-source dot, methods footer below the tree.
```

`--one-per-species` is a readability choice with a measurable biological cost. On live project
panels, thinning a 106-reference backbone to 46 references produced 71 terminal query branches over
0.5 substitutions/site, while the denser backbone produced none; a thin core-genome panel also moved
a supported genus-level topology. High support describes the selected panel. It does not show that
the reference sampling was adequate. Compare sparse output against a denser backbone before using it
for interpretation. `--one-per-genus` is available for deliberately sparse overview figures and
must not be the only backbone used for biological interpretation.

For publication displays, keep the dense fixed backbone for EPA-ng placement and render a balanced
three-level ladder with `placement_display.py --neighbors-per-query 1`, `2`, and `3`. Each level takes
the union of every query's nearest one, two, or three reference tips, with deterministic distance/name
tie handling. The producer writes `<name>_reference_selection.tsv`, which records each query-to-reference
pair, neighbor rank, and patristic distance. This keeps the display bounded at no more than the selected
query:reference ratio while avoiding a global top-reference list dominated by one query or one dense
species group. `--keep-all-references` is retained for diagnostic displays and is explicit.
Every rung must still pass the tree gate. A 1:1 rung can be refused when severe pruning makes one
contracted path dominate the displayed tree; preserve that refusal and use the first passing denser
rung rather than weakening the branch-length check.

Within the selected display, a monophyletic set of references can be grouped only when every member has
the same deposited binomial species and every pair differs by at most one nucleotide over at least 500
shared A/C/G/T positions. The representative label reports the number grouped and measured bounds; the
ledger retains every accession and strain designation. This is a display reduction, not a same-strain claim.

### One strain under multiple accessions

NCBI may hold separate 16S records under different culture-collection names for the same biological type strain. String matching cannot safely infer those synonyms. Before reference-tree inference, `phylo_place.py` collapses only exact sequences, identical normalized strain designations, and accession pairs present in the reviewed `mamey/data/16s_reference_strain_aliases.tsv` registry. Every decision is recorded in `reference_dedup.tsv`; unlisted same-species records remain separate and generate a curator warning. Extend the reviewed TSV or pass `--strain-aliases <TSV>` rather than deduplicating by similar-looking names.

A current species name can also contain several historically distinct type cultures after taxonomic
synonymization. Shared species labels or shared source text therefore do not prove that two accessions
are the same biological strain. Use `--one-per-species` when the display calls for one representative
per accepted species, and reserve the alias registry for accession/designation pairs supported by a
reviewed culture or taxonomy record.

Panel FASTA files use stable accession-only tip IDs, so `--one-per-species` also requires the explicit
`--reference-metadata` sidecar from `phylo_16s_panel.py`. The build refuses query-role rows in that
reference FASTA. Without the sidecar, unknown species stay separate; they are never merged under a
fabricated key derived from `REF_NR_...`.

## Governing rules (baked into the tools)
1. **Source separation.** One genus/cohort per tree. `--group` is required and stamped into every output;
   a single genus is the strictest separation (EGGPLANT_411 per-genus patch).
2. **Registry outgroup, rooted.** The outgroup is looked up in `OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv`
   (e.g. Actinomadura → *Actinocorallia herbida* GCF_003751225.1 / NR_115631.1, LOCKED — sister genus, not
   *Spirillospora* which nests inside Actinomadura). build-ref appends it and roots the backbone on it.
3. **No foreign-genus sentinels.** On a per-genus backbone with a registry outgroup, off-genus "sentinel"
   records are stripped before inference (they otherwise dominate the tree and FAIL sanity).
4. **Gates before render.** `tree_sanity_check` (outgroup-aware) must PASS. `phylo_postflight` P3 is
   placement-aware (a graft carries no tree-wide UFBoot; confidence = LWR + backbone Felsenstein bootstrap).
5. **The prune ladder.** `--neighbors-per-query N` (figure) / `--neighbors N` (producer) renders a series:
   N=1 tight, N=3 medium, `--keep-all-refs` full. The full backbone size is always stated.
6. **Honest labels.** Query tips = strain / host / 16S GenBank accession from the paper strain table (the
   authoritative host source; NOT `host_common`, which had defects). Reference tips carry an **isolation
   source** dot (soil / soil-rock / plant / lichen / insect-associated / clinical-animal / other / unresolved),
   curated from species-description papers + BacDive — never invented; "unresolved" where no source is found.
   The outgroup is **not** an isolation source and carries no dot.
   A project strain accession found in the reference role is a hard refusal; the display reports how
   many project accessions were checked. Project strains are references only in a separately declared,
   receipt-bound analysis with an explicit role ledger.
7. **Methods travel with the figure.** `GG_METHODS` prints a wrapped methods block below the tree, so a bare
   image is still a complete, sourced deliverable.

## Confidence reading
LWR ≥ 0.8 = "within" that clade's neighbourhood; LWR < 0.4 = report as "near", not "in". A denser reference
lowers LWRs (finer ambiguity), which is more honest, not worse. A long pendant length = a divergent query.

## Package layout (self-contained deliverable)
```
<run>/
  METHODS.md                       question, provenance, exact command, tool versions, LWR table, denominators
  inputs/                          harvested reference 16S + query 16S
  tree/placement/                  jplace, grafted newick, placements TSV, neighborhoods, refpkg (+ FBP support)
  ggtree/                          pruned.nwk, annotation TSV, isolation_source.tsv, PDF+PNG (ladder rungs)
  logs/                            build log, tool provenance (versions)
```

## Version-matched tools
raxml-ng 2.0.2 · EPA-ng 0.3.8 · gappa 0.9.0 · mafft 7.526 · Biopython 1.87 · ggtree 4.2.0 / R 4.6.0 ·
Sapote-Mamey phylo_place (engine 1.9.149). Cite the exact installed versions (`mamey doctor`).


## Overlay a binary bioassay summary

A placement tree can display a supplied strain-level summary for Candida and MRSA. Prepare a CSV or TSV with exactly one row per strain and the columns `strain`, `anti_Candida`, and `anti_MRSA`. Result cells accept `positive`, `negative`, `not_tested`, or blank. A blank cell or absent row means **not recorded**, not negative and not proof that no assay was performed. Duplicate strain rows, conflicting results, unsupported values and malformed tables are refused. Summarize replicate, fraction and concentration data explicitly before making this binary table; the tool does not select thresholds or aggregate experiments.

```bash
python3 tools/build_placement_ggtree_inputs.py \
  --graft /path/to/placement.newick \
  --bioassay-table /path/to/bioassay_summary.csv \
  --out-prefix /path/to/output/placement
Rscript tools/ggtree_placement_bioassay.R \
  /path/to/output/placement_pruned.nwk \
  /path/to/output/placement_ggtree_annotation.tsv \
  /path/to/output/bioassay_overlay noloc
```

For a tree containing several reference genera, add `--family-level` to the producer so other genera are not automatically treated as outgroups. Supply the appropriate outgroup selection for your analysis. The overlay draws two squares beside query tips, Candida then MRSA; reference tips receive none. The legend distinguishes positive, negative, explicitly not tested and not recorded. The renderer writes PNG and PDF; its title does not infer the tree-building method or assay preparation. Use `GG_TITLE`, `GG_SUB`, or `GG_METHODS` to supply verified descriptions when needed.

The table is an input summary, not independent verification of the experiment. Preserve its assay conditions, source records and interpretation criteria with the analysis; the producer binds the input file hash. An overlay associates results with strains and does not assign activity to an individual gene cluster or compound.


## Display a completed placement run

Split a panel by its recorded roles before building a reference backbone:

```bash
python tools/panel_split.py panel.fasta panel_meta.tsv --out-prefix work/panel
```

The resulting reference FASTA includes the declared outgroup. The query FASTA contains only
query records. Duplicate identities, missing roles and an empty side refuse. Existing output
files are protected.

After placement and reporting, render into a new directory:

```bash
python tools/placement_display.py work/run --name panel --group Example \
  --host-table metadata/hosts.tsv --ref-source-db metadata/reference.sqlite \
  --family-level --label-style withloc --out work/display_withloc
python tools/placement_display.py work/run --name panel --group Example \
  --host-table metadata/hosts.tsv --ref-source-db metadata/reference.sqlite \
  --family-level --label-style noloc --out work/display_noloc
```

The run must contain `report/epa_result.newick`, `refpkg/ref.aln.fasta` and
`place/query.aligned.fasta`. Use `--family-level` only for a panel intentionally spanning genera.
The wrapper uses the current bundled annotation builder, display receipt and tree gate. It
preserves every tip, refuses accession conflicts and requires a new output directory for each run.
A failure leaves an incomplete new work directory without a completion receipt, and preserves
previous outputs and the original analysis inputs.

`noloc` removes the structured country/location label fields and Location strip, while keeping
habitat. Unresolved geography embedded in a reference label refuses instead of silently claiming
it was removed. Optional `--genus-roster` reads an explicitly selected TSV with `strain` and
`genus` (or `tophit_genus`), rejects duplicate identities, and prefixes query labels with that
recorded genus. It does not certify the taxonomy. Reference organism labels can use the
explicit reference database's `definition` field. Conflicting definitions refuse. Reference
collapse requires recorded taxon metadata; missing taxa are not guessed.

Use `--aux-table` for an explicit accession table. `tools/panel_receipt_to_aux.py` can export
query accessions from a panel receipt to a new TSV, preserving blank host/location fields.
Conflicts remain subject to the annotation builder's existing checks.

Representative grouping labels report the observed maximum nucleotide differences and minimum
shared unambiguous sites. They do not label threshold-based grouping as sequence identity.
Reference terminal disagreement is written to `TERMINAL_DIVERGENCE.tsv` as an advisory metric;
the reference alignment used for inference is not masked or rewritten by this assessment.

Tip labels do not include an outgroup annotation. The default caption identifies the bound outgroup; a supplied `--methods` caption replaces it and should identify the outgroup itself. `--fig-id` supplies the figure identifier. Gate and display notes remain in
receipts and the renderer's `.methods.txt` sidecar, rather than being appended to final figures.
The completed display receipt records source hashes, output hashes and the label style. Its
presence establishes successful processing, not scientific acceptance of a prior analysis.
`DROPPED_TIPS.tsv` is always emitted, including as a header-only table when no tip was removed;
the complete collapse decisions remain in `*_collapse_ledger.tsv`.

Labels use `[isolation source] (ACCESSION)`, omitting the terminal accession version only in display text. Versioned keys remain in data and provenance. The scale bar floats below the tree, separate from branches.

Every query must have a valid GenBank accession in the selected host or auxiliary table. Both label variants must show the matching accession; missing or mismatched query accession labels refuse before rendering.
