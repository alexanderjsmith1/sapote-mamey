# Add another view of a package

Three optional commands add a second view to an extracted package:

- `gecco-crosscheck` compares the package's regions with a second caller, GECCO.
- `export-metabolomics` writes genome-side files for a mass spectrometry (MS) workflow.
- `two-proof-rescue` re-reads candidate fragment pairs from RG-GMCI.

A package is the folder `run` builds and `validate` checks; see the
[first-run page](reader/01_FIRST_RUN.md). You also need the original antiSMASH
ZIP. Run the examples from the program folder. Replace `EXAMPLE` and the ZIP path.

Each command writes to `post_seal/<command>/` next to the package folder (for
example `runs/EXAMPLE/post_seal/<command>/`), outside the package. For another attempt, pass `--out` with a new folder. An existing
destination is refused, even when empty (`COMPANION_OUTPUT_EXISTS`). Keep the
package and source files unchanged while a command runs.

Every command prints one line on success and exits 0. On refusal it prints a line
that names a code and exits 2. The sections below give both lines.

## GECCO

Get a second set of cluster predictions from the same genome. GECCO is a
separate program that predicts biosynthetic gene clusters. The bundle's add-on
installer (`bundle_support/install_sapote_addons.sh`) suggests a separate environment:

```bash
conda create -n gecco -c conda-forge -c bioconda gecco=0.11.0
```

Do not run Mamey inside that environment; its Python lacks Mamey's packages. Instead,
keep Mamey's environment active and put GECCO's program folder on `PATH`. Mamey only
looks for a `gecco` command on `PATH`:

```bash
export PATH="$(conda run -n gecco sh -c 'echo $CONDA_PREFIX')/bin:$PATH"
gecco --version
python mamey_run.py doctor --companions
```

`gecco --version` must print a 0.11 version. `doctor --companions` reports the
local probe state; a missing executable or failed probe does not fail `doctor`.
Read the state and install hint as described in the [companion tool guide](COMPANION_TOOL_GUIDE.md).
The command repeats the version check before it starts. Then run:

```bash
python mamey_run.py gecco-crosscheck --package runs/EXAMPLE/package \
  --zip ~/Downloads/EXAMPLE.zip
```

The defaults are a probability threshold of 0.8 and one job. Change `--threshold`
or `--jobs` only for a deliberate analysis/resource choice. The adapter launches
GECCO on the whole-genome GenBank member of the package-bound ZIP. If the ZIP has
several eligible genome members, choose one with `--genome-member`.

You should see:

```text
GECCO cross-check: N locked regions; external outputs only
```

If GECCO is missing or is not 0.11, or Biopython is missing, you see one of these instead, and the
command exits 2:

```text
GECCO cross-check refused: GECCO_NOT_INSTALLED: optional companion; bundle does not install it
GECCO cross-check refused: GECCO_VERSION_UNSUPPORTED: this adapter targets the 0.11 CLI/table contract
GECCO cross-check refused: GECCO_BIOPYTHON_MISSING: ...
```

Biopython is needed in the Python that runs Mamey (the `bio` extra), separately from the GECCO
executable on `PATH`.

Open the output's `*_7_gecco_vs_antismash.csv`,
`*_7_gecco_only_clusters.csv` and `*_7_gecco_gene_probabilities.csv`.
The folder also contains the selected genome, raw outputs, log, support file and
receipt. GECCO-only means no overlap with this package's selected region roster.

A version probe has a 15-second timeout; the analysis has no adapter timeout.
On failure, keep the terminal output: a failed native run can lose its staged
files before `gecco.log` is written. The receipt's recorded command contains
staging paths, so use your published paths when reading its outputs later.

### Check GECCO joins and coordinates

The returned gene table must match the full source CDS roster, contigs and
coordinates. Blank or NA probabilities stay unknown. A present but invalid
probability is an error. The gene CSV uses **1-based inclusive** coordinates.
GECCO-only cluster intervals use **zero-based half-open** coordinates. Convert
explicitly when you join them.

To pass a copied gap-gene table, repeat `--gap-genes` for each file. A file ending
`.tsv` (lowercase) is read as tab-separated. Any other suffix is read as
comma-separated. A row needs at least one of `locus_tag`, `query_gene` or
`protein_id`. When several are present, their nonblank values must agree. Give
complete start and end pairs for coordinate checks. The copied table adds GECCO
columns, so an input that already has them is refused.

| Input problem | Refusal code |
|---|---|
| Unsupported table columns | `GECCO_GAP_GENE_SCHEMA_UNSUPPORTED` |
| Start and end columns incomplete | `GECCO_GAP_COORDINATE_SCHEMA_INCOMPLETE` |
| Start and end not whole numbers, or out of order | `GECCO_GAP_GENE_COORDINATE_INVALID` |
| Coordinates differ from the package gene | `GECCO_GAP_GENE_COORDINATE_MISMATCH` |
| ID columns disagree, or match several genes | `GECCO_GAP_GENE_ID_AMBIGUOUS` |
| Row belongs to another strain | `GECCO_GAP_GENE_STRAIN_MISMATCH` |
| Contig is missing or matches several | `GECCO_GAP_GENE_CONTIG_AMBIGUOUS` |
| Contig differs from the package gene | `GECCO_GAP_GENE_CONTIG_MISMATCH` |
| Two inputs would write the same output name | `GECCO_GAP_OUTPUT_NAME_DUPLICATE` |

Read `gecco_join_state` and `gecco_binding_scope`. A tag-only match is labeled
`SOURCE_LOCUS_TAG_ONLY`; unknown tags stay unmatched. Your original tables are
unchanged. Keep the support file, receipt and raw outputs together.

## Genome-side metabolomics files

Prepare region GenBank files and class hypotheses for an MS workflow. NPLinker
is a tool that matches MS data to gene clusters. PoDP, the Paired Omics Data
Platform, is a public store for paired genome and metabolomics records. The
command writes files in the layout NPLinker reads and a template for a PoDP
record. A class hypothesis is a cluster class that the genes support, not a
compound.

```bash
python mamey_run.py export-metabolomics --package runs/EXAMPLE/package \
  --source-zip ~/Downloads/EXAMPLE.zip
```

`--source-zip` supplies the original archive: a recorded relative path may not
resolve from the package folder. Its hash must match the package manifest.
Add `--gecco-dir` only for a matching GECCO crosscheck output.

You should see:

```text
Metabolomics export: N class hypotheses; MS sample mapping requires operator completion
```

Open `*_metabolomics_targets.tsv`, `metabolomics_targets.json` and
`nplinker/antismash/`. The export also writes source pointers, strain mappings,
a PoDP record template, README and receipt. Compare the exported region count
with the package inventory.

The export admits only real region GenBank files (`.regionNNN.gbk`). If a locus
has none in the archive, the export stops:

```text
Metabolomics export refused: METABOLOMICS_REGION_SOURCE_UNBOUND
```

Use the full antiSMASH archive. [Input contents](ANTISMASH_INPUTS_CONSUMED.md)
says which files it must hold.

Fill the MS sample mapping and metadata from your own experiment.
`OPERATOR_COMPLETION_REQUIRED`, null fields and an empty sample list mark an
unfinished template. JSON lists inside TSV cells stay serialized JSON.

## Candidate fragment pairs

RG-GMCI (Reference-Guided Genome Mining Candidate Inference) proposes that two
fragments on separate contigs belong to one cluster, because they match different
parts of the same reference cluster. `two-proof-rescue` asks for a second,
separately computed reason before it calls such a pair supported. Every second-proof
channel is computed from the same antiSMASH result as the candidate review, so it is
computational corroboration, not independent source evidence and not validated
physical linkage. The `second_proof_source_dependency` column of the 4D table says
which shared source each channel uses: the KS clade comes from the package's own KS
scan, core completion from the same archive, and the position reading from the same
ClusterBlast hits as RG-GMCI. The column name `independent_proof_state` is kept for
compatibility; read it as "second-proof state". It recomputes the saved
pair review from the original archive. See the [glossary](GLOSSARY.md#7-rg-gmci-and-the-rescue-layer).

```bash
python mamey_run.py two-proof-rescue --package runs/EXAMPLE/package \
  --input-zip ~/Downloads/EXAMPLE.zip
```

The default `class_routed_v1` policy uses the ketosynthase (KS) clade check for
KS-bearing pairs.
For eligible non-KS pairs, it checks whether the members together complete their
class core when neither does alone. It also reads position evidence and marker
conflicts. Keep the policy with every reported result.

You should see:

```text
Two-proof reader: N pairs; policy=class_routed_v1; adjudication required
```

Open `*_4D_two_proof_rescue.csv` and `receipt.json`. Read the full `identity_a`
and `identity_b`, verdict, `second_proof_channel`, `independent_proof_state`,
`position_verdict` and `position_reference`. The package needs exactly one
`*_4A_RGGMCI_ranked_pairs.csv`, the RG-GMCI pair table that `run` writes. If it
is missing, or there are several, the command stops with
`NONKS_RGGMCI_INPUT_AMBIGUOUS`; this reader uses stored domain/KS evidence.
A successful command can produce zero pairs or unresolved results. A refusal reads
`Two-proof reader refused: <CODE>`.

The position reading shares ClusterBlast evidence with RG-GMCI, so it is not
independent of it. Treat its verdict as a prompt to look, not a result. Keep the
candidate contigs separate while you review the proposed relationship.

### Use a supplied non-KS scorecard

Choose this route only when your task calls for the scorecard-based policy:

```bash
python mamey_run.py two-proof-rescue --package runs/EXAMPLE/package \
  --policy nonks_position_v1 --scorecard reviews/EXAMPLE/scorecard.tsv \
  --out reviews/EXAMPLE/nonks-review
```

`--policy` selects that alternative; `--out` keeps it separate from the default
review. A scorecard is a tab-separated file with one row per candidate pair. The
default policy builds the same readings itself from the archive, so you only need
a scorecard when you already have one, for example from an earlier review. The
columns are `strain`, `identity_a`, `identity_b` (each the full identity text
from the `4A` table), `layers_verdict` and `relative` (the shared reference
cluster). A `pair` column is optional. Example:

```text
strain	identity_a	identity_b	layers_verdict	relative
EXAMPLE	EXAMPLE / contig_1 / region001 / BGC001	EXAMPLE / contig_9 / region002 / BGC007	CONSISTENT	BGC0000001
EXAMPLE	EXAMPLE / contig_2 / region001 / BGC002	EXAMPLE / contig_5 / region001 / BGC004	APART_CLOSE	BGC0000002
EXAMPLE	EXAMPLE / contig_3 / region003 / BGC003	EXAMPLE / contig_8 / region001 / BGC009	NOT_READ
```

`layers_verdict` values the code writes:

| Value | Meaning |
|---|---|
| `CONSISTENT` | Both fragments hit one reference cluster, and their best loci lie within 50 genes of each other there. |
| `APART_CLOSE` | The loci are farther apart in a complete reference matched at 70% mean identity or more by both. |
| `APART_WEAK` | Farther apart, but the reference is a draft or the match is weaker than 70%. |
| `CONFLICT` | Both fragments carry a complete single-copy marker gene, so they are probably two clusters. |
| `NOT_READ` | No shared reference, so position could not be read. |

Compare the requested and consumed pair counts:
rows for another strain are skipped, and an unknown verdict spelling leaves the
position check unresolved. A missing scorecard can also produce unresolved rows.

Some scorecard faults stop the command instead:

| Scorecard problem | Refusal code |
|---|---|
| `identity_a` or `identity_b` is not in this package, or both are the same | `NONKS_SCORECARD_LOCUS_BINDING_MISMATCH` |
| The same pair appears twice | `NONKS_SCORECARD_DUPLICATE_PAIR` |
| The `pair` column disagrees with the two identities | `NONKS_SCORECARD_PAIR_ID_MISMATCH` |
| `--policy` names an unknown policy | `NONKS_POLICY_UNSUPPORTED` |

This policy requires complementary HIGH linkage, an observed eligible non-KS core
and a CONSISTENT scorecard reading naming a relative. `APART_CLOSE` or `CONFLICT`
vetoes an eligible pair; unavailable or weak position evidence leaves it unresolved.
KS-bearing candidates keep the KS rule. `--policy ks_clade_v2` selects the earlier
KS-only policy when needed for a comparison.

A fallback based on disjoint references can report `independent_proof_state`
PRESENT without changing the earlier verdict. Read the two counter columns in the
`4A` table, `complementary_disjoint_refs` and `overlapping_subject_refs`. The fallback
needs at least 3 disjoint references and an overlap count of 0. When the
`overlapping_subject_refs` cell is blank or malformed, or the whole column is absent
(a 4A table made before the column existed), the overlap is unmeasured and the logic
proof is unresolved (`LOGIC_EVIDENCE_HOLD`). A missing column is never read as zero
overlap. For the absent-column case the row's `claim_note` adds "overlap count absent
(legacy _4A without overlapping_subject_refs); held as unmeasured, not read as zero;
re-run the package to measure it". Re-running the package writes the column. The 4D
`two_proof_logic_version` is `4` from this rule on; packages read under version `3`
could show such rows as `RGGMCI_ONLY` or `TWO_PROOF_RESCUE`.
A high overlap count beside a high disjoint count is a competing reading: the two
contigs may carry duplicate or paralogous copies of the same machinery, or other
explanations may apply. It needs pair-specific review; the counts alone do not settle
paralogy. Do not treat PRESENT as a finished result. Keep unresolved KS-only rows without invented
locus assignments.

The receipt records hashes of the RG-GMCI table and the scorecard. It records the
input ZIP hash only when positions were read from the archive. It does not hash the output CSV, so record that hash yourself.

## If a command stops

Read the terminal error and keep the original package. Outputs inside the package
and package symlinks are refused. An interrupted attempt can leave a hidden
staging folder; inspect it with the log and retry at a new destination after
fixing the cause. These readers use `--package` followed by the extracted package
folder, rather than a package ZIP or run root.

<a id="genome-side-metabolomics-bridge"></a>
<a id="second-proof-policy-routed-by-class"></a>
<a id="package-argument-syntax"></a>
