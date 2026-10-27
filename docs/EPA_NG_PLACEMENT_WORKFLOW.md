# EPA-ng 16S placement: candidate workflow and mechanical gates

**Lane:** The phylogeny lane · **Engine:** sapote-mamey ≥ v9.7.411 (needs the 411 patches) · **Status:** shipped companion stages; execution, complete output coverage and scientific acceptance require separate receipts.
Read alongside the corrected `docs/PHYLO_PLACEMENT_WORKFLOW.md`, which referenced a producer (an older unpackaged producer script)
that was never packaged, leaving the ggtree renderer orphaned. This workflow is self-contained: every step
is a shipped tool.

> **Claim-safety (governing).** 16S rRNA is a phylogenetic **anchor / clade-neighbourhood** indicator, **not**
> a species assignment. A placement states the genus/clade neighbourhood a query falls into on a FIXED
> reference backbone, with a per-query **likelihood-weight ratio (LWR)** as relative placement weight. No ANI/AAI, no
> bioactivity/structure claims; judgment deferred.

## When to use this
16S-only strains (no genome), or a fast neighbourhood read before a genome/MLSA tree. Queries are **placed**
on a fixed type-strain backbone; they never perturb its topology. For genome trees use `docs/GTOTREE_WORKFLOW.md`.

## Environment (read first)

`miniconda3/`, `blast_dbs/` and `Tools/databases/` are **workspace** assets; the CODE bundle does not
ship them. Helpers that use `workspace_root()` prefer `SAPOTE_WORKSPACE_ROOT`,
then `SAPOTE_ROOT`. Without an override, they search the current directory and its
ancestors for the nearest workspace marker; the current directory is the fallback
only when no marker is found. Pin the intended workspace once per shell. Before
running `doctor`, check its [reserved write-probe path](INSTALL.md#doctor-scope-and-write-probe)
and use an editable working installation:

```bash
export SAPOTE_WORKSPACE_ROOT="/path/to/your/workspace"      # the folder that contains miniconda3/ and OFFICIAL_DATA/
export BLAST_BIN="$SAPOTE_WORKSPACE_ROOT/miniconda3/envs/blast/bin"
export PATH="$SAPOTE_WORKSPACE_ROOT/miniconda3/envs/placement/bin:$PATH"
python mamey_run.py doctor        # reports blastdbcmd / mafft / raxml-ng / epa-ng / gappa / Rscript
```

`harvest_16s.py` auto-locates its inputs and yields `query 0/N` rather than refusing when they are
missing; pass `--authoritative`, `--refseq-db` and `--blastdbcmd` explicitly for a reproducible run.

## The pipeline (one command per stage)

These are prospective command shapes. Run from the selected bundle root with its compatible interpreter. Current `all` writes a fresh `graft_length_evidence` child under the selected output; after numerical admission, resolve `<admitted-restored-graft>` from that receipt’s selected restored output, rather than guessing `epa_result.newick`. A held or occupied evidence child is preserved and cannot be treated as a completed current render. The later `placement_display.py` route performs its own source-bound length re-admission.

```
python tools/phylo_place.py all <ref_16S.fasta> --group <Genus> --query <queries.fasta> \
     --reference-metadata <ref_16S_meta.tsv> \
     --add-outgroup <Genus> --approved-by "<recorded-approval>" --one-per-species --bootstrap 10 --outdir <run>/placement
     # build-ref (mafft → raxml-ng GTR+G, rooted on the registry outgroup) → EPA-ng place → gappa graft → report
     # driver interpreter: Tools/bin/python3 (Biopython); binaries: miniconda3/envs/placement/bin
     # → epa_result.jplace, epa_result.newick, <Genus>_placements.tsv, <Genus>_neighborhoods.tsv, refpkg/

python tools/phylo_postflight.py <admitted-restored-graft> --outgroup <OutgroupGenus>
python tools/tree_sanity_check.py <admitted-restored-graft> --outgroup <OutgroupGenus>

python tools/build_placement_ggtree_inputs.py --graft <admitted-restored-graft> --group <Genus> \
     --neighbors <N> --host-table <paper strain table> --origin-table <isolation_source.tsv> \
     --ref-source-db <16S store with record(acc_base, definition)> \
     --outgroup-substr <OutgroupGenus> --out-prefix <run>/ggtree/<Genus>
     # → <Genus>_pruned.nwk + <Genus>_ggtree_annotation.tsv (host+accession on queries; isolation-source on refs)
     # --ref-source-db has NO default and NO automatic discovery. Omit it and every reference tip is
     # NOT_REQUESTED and renders bare -- the line above promises isolation-source on refs, and only this
     # flag delivers it. The producer now says so on stderr; reference_source_status records it per tip.

GG_TITLE="..." GG_METHODS="<full methods paragraph>" \
Rscript tools/ggtree_placement.R <run>/ggtree/<Genus>_pruned.nwk <run>/ggtree/<Genus>_ggtree_annotation.tsv \
     <run>/ggtree/<Genus>_fig noloc
     # → candidate PDF + PNG: queries red/bold (host + 16S accession), refs blue with an
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
   authoritative host source; NOT `host_common`, which had defects). Reference tips carry the
   **deposited isolation-source text** from `--ref-source-db`, in the label form
   `[isolation source] (ACCESSION)`. The source is reported as deposited and is not binned into categories.
   A reference with no deposited source carries no source text.
   A project strain accession found in the reference role is a hard refusal; the display reports how
   many project accessions were checked. Project strains are references only in a separately declared,
   receipt-bound analysis with an explicit role ledger.
7. **Methods travel with the figure.** `GG_METHODS` prints a wrapped methods block below the tree, so a bare
   image is still a complete, sourced deliverable.

## Confidence reading
LWR is the relative weight of a placement edge among the retained alternatives, not a bootstrap,
species probability or universal clade-confidence threshold. Report the best and alternative
placements, retained weight sum, reference scope and branch-length provenance. Panel changes can
change those weights; there is no guaranteed direction. Long pendant length requires review of
query, alignment and reference scope before interpretation.

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

The splitter copies rows with exact `reference` or `outgroup` roles to the reference FASTA and exact `query` rows to the query FASTA. It checks duplicate tips/headers, role membership and empty sides, but does not require an outgroup or verify taxonomy, nucleotide alphabet or biological identity (`tools/panel_split.py`). The CLI checks the three output paths with `exists()` before sequential direct writes; it has no exclusive reservation or transactional rollback. A race or dangling symlink can defeat that precheck, and a late failure can leave partial outputs. Use a fresh prefix in an existing destination directory, keep source/output paths distinct, and verify both FASTAs and the receipt; the input hashes are taken before output writes.

After placement and reporting, render into a new directory:

```bash
python tools/placement_display.py work/run --name panel --group Example \
  --host-table metadata/hosts.tsv --ref-source-db metadata/reference.sqlite \
  --family-level --label-style withloc --out work/display_withloc
python tools/placement_display.py work/run --name panel --group Example \
  --host-table metadata/hosts.tsv --ref-source-db metadata/reference.sqlite \
  --family-level --label-style noloc --out work/display_noloc
```

Current display admission requires exactly one source-bound `graft_length_evidence/receipt.json`, at the run root for the declared flat layout or under `report/` for the declared nested layout. It rechecks numerical length evidence, selected restored tree, exact jplace/reference/model/provenance bindings and both alignments; three familiar filenames alone cannot admit an old run (`tools/graft_integrity.py`). Use `--family-level` for an intentionally mixed-genus panel and bind its query genus roster; the wrapper can also enable family-level handling from recorded reference genera (`tools/placement_display.py`).

The wrapper requires a new output directory and checks initial tree/alignment coverage. Reference selection and collapse intentionally change the displayed roster; inspect the selection and dropped/collapse ledgers rather than assuming every reference tip remains. A later failure can leave rendered files **and** `placement_display_receipt.json`: that file is written before standalone-package export, required-file checks and final source re-admission. Require the actual zero exit, complete expected package/page roster, unchanged-source checks and rendered-page review. Receipt presence alone is not a terminal completion proof.

`noloc` removes the structured country/location label fields and Location strip, while keeping
habitat. Unresolved geography embedded in a reference label refuses instead of silently claiming
it was removed. Optional `--genus-roster` reads an explicitly selected TSV with `strain` and
`genus` (or `tophit_genus`), rejects duplicate identities, and prefixes query labels with that
recorded genus. It does not certify the taxonomy. Reference organism labels can use the
explicit reference database's `definition` field. Conflicting definitions refuse. Reference
collapse requires recorded taxon metadata; missing taxa are not guessed.

Tip labels carry the geography as deposited, for example `Panama: Barro Colorado Island`. They are
not binned to continents. A tip with no deposited geography gets no geography word, and none is
inferred. The Location strip still colors by continent. `--geography-level` sets the label
geography. `SAPOTE_GEOGRAPHY_LEVEL` does the same for `build_placement_ggtree_inputs.py`.
`deposited` is the default. `region` puts the continent bins on the labels too; use it to
reproduce a render from an older bundle. `country` puts the deposited country on the labels and
the strip.

Use `--aux-table` for an explicit accession table. The local `tools/panel_receipt_to_aux.py` adapter exports the selected 16S panel receipt's query accessions; it neither fetches records nor runs placement. From the selected bundle root, with its Python/bundled CSV helper available:

```bash
python tools/panel_receipt_to_aux.py \
  "/absolute/source/panel_panel_receipt.json" \
  --out "/absolute/new_metadata/query_accessions.tsv"
```

Create the output parent first and use a fresh path outside source evidence. This consumer requires a JSON object with a `records` list, such as the receipt emitted by `phylo_16s_panel.py`. The genome-panel `build_phylo_panel.py` receipt has a different schema and is not interchangeable merely because its filename is `panel_receipt.json`. Only records with exact `kind=query` are considered. Query tips must be unique nonempty strings using letters, digits, underscores, periods or hyphens; accessions must match the adapter's uppercase accession syntax, with an optional version. It checks neither receipt status/schema version nor source/sequence hashes or live accession identity.

The TSV columns are `strain`, `host`, `region`, `accession`; `strain` receives the exact receipt tip, while host and region are deliberately blank even if present in the receipt. Falsy/missing query accessions are silently skipped after their tip is checked. All skipped produces `NO_QUERY_ACCESSIONS`, but a mixture of bound and unbound queries can exit 0 with a partial roster. Reconcile exported rows with every intended query and retain the unbound/local-query holds; this export does not make those queries eligible for the accession-required display route.

The adapter refuses an existing output and uses exclusive creation, preventing a concurrent replacement. It writes the TSV directly, so a late write failure can leave a partial file that a retry refuses. Preserve the partial and use a fresh destination after correcting the cause. Success exits 0; caught JSON/validation/I/O errors log a refusal and exit 2. The standalone script does not configure INFO logging, so its success message is normally suppressed. Inspect the output and exit status; no JSON completion receipt or input/output hash inventory is emitted. Record those hashes separately.

Pass the TSV explicitly as `--aux-table` only after checking its keys against the selected annotation consumer. That consumer fills empty host/region/accession fields and refuses conflicting nonempty values; it does not use blank auxiliary cells to erase prior metadata. Its recognized AS tip IDs can be normalized to `AS-<digits>`, whereas this exporter preserves the exact tip spelling. Reconcile any key spelling/role mismatch with source-bound metadata instead of assuming an exported row joined the displayed query. Conflicts remain subject to the annotation builder's existing checks.

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

## Current source contract and historical observations

The source guards `build-ref` with a nonempty `--approved-by` record and, when its bundle stamp is present, refuses the resolved refpkg destination inside the executing code bundle. The all-stage example must bind actual approval and an external candidate output. The field records supplied authorization; a nonempty string does not authenticate a scientific owner decision (`tools/phylo_place.py`). Registry authority comes from a selected governed external registry, not the bundled reference-only rows; historical named outgroups in this page are illustrations, not authority for a new tree. See [outgroup/refset limits](OUTGROUP_AND_REFSET_WORKFLOW.md).

`all` reuses a supplied `--refpkg` when its `ref.tree` exists; otherwise it builds a reference package (`tools/phylo_place.py`). Bind the complete input/model/tree/version/approval record first; existence alone is not freshness or panel identity. Current reporting produces source-bound numerical length evidence before admitting neighborhood distances or rendering; unverified length evidence holds those products. Inspect `<group>_REPORT_ATTEMPT.json`: report completion requires admitted lengths and, when requested, strips in RENDERED or RENDERED_WITH_OMISSIONS state. A strip/length hold returns2. An optional diagnostic-render failure can still be caught without blocking a report whose other completion conditions pass. Check the requested deliverable roster independently.

The native diagnostic renderer writes PNG200dpi, SVG and labels JSON. The label JSON binds the input tree and stores the labelmap/roles, while the returned render descriptor separately hashes PNG, SVG and labels JSON. It is no longer accurate to describe the current report path as lacking any rendered-artifact binding; those hashes still do not establish biological correctness or visual usability.

Outgroup role tokens are preferred; when absent, the native diagnostic renderer retains a modal-organism-genus heuristic (`tools/phylo_place.py`). A mechanical gate or display-root convention does not establish biological outgroup suitability. Detailed alternatives are exported to `<group>_placement_alternatives.tsv`, with retained LWR sum/count, without renormalization; `<group>_placements.tsv` is the separate best-hit table. `uncertainty_measure` explicitly reads `LWR_NOT_BOOTSTRAP_OR_SPECIES_PROBABILITY`.

The 106→46 reference thinning example, installed version list and project strain-table paths are historical project observations. They need their exact source hashes and run receipts before reuse, and do not set current panel adequacy or installed versions. “Methods travel” describes a renderer/display policy, not proof that a bare image contains complete acquisition provenance or passed visual review. Record actual placement, dependency and render receipts separately. Preserve source assets in place and carry path+SHA-256 and scope through every stage.
