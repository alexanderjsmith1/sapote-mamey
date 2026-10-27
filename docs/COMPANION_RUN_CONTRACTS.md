# Companion run contracts for people and assistants

This guide
describes local code behavior. Use the current user request and existing matching authorization
before executing tools. Preserve immutable inputs and select fresh outputs outside the
code bundle. External tool/database installation is separate from core installation.

## Select the operation

| Operation | Inputs | Actual work and writes | Read to assess completion |
|---|---|---|---|
| `tools/phylo_autopilot.py plan <dir>` | local FASTA directory | Reads sequence records; prints classification JSON | Printed categories and sequence inspection; no tree is inferred |
| `tools/phylo_autopilot.py route --query ... --db ... --out ...` | nucleotide queries and local BLAST database prefix | Executes `blastn`; writes routing TSV | Routing states, query coverage, excluded/conflicting assignments and subprocess diagnostics |
| `tools/phylo_autopilot.py run-16s ... --dry-run` | same local database plus selected group/output root | Executes routing BLAST and reference `blastdbcmd`; writes QC, routing, accession list and FASTAs | Prepared roster and actual reference/type provenance; no placement is performed |
| `tools/phylo_autopilot.py run-16s ... --approved-by ...` | prepared local source scope | Same preparation, then delegates `phylo_place all` | Reference provenance, jplace, placement tables, render warnings and actual requested files |
| `tools/build_mlsa.py <genomes_dir> <new_out>` | immediate lowercase `*.fna` genomes and five protein seed files | Prodigal, seed BLAST, alignment, available-locus concatenation and IQ-TREE; external binaries required | `loci_report.tsv`, retained partitions/tips, `run_status.json`, log and actual tree; missing loci/taxa are not complete five-locus coverage, and no 16S partition is produced |
| `tools/plan_gtotree_iqtree.py plan ...` | prepared panel or manual panel TSV, HMM, toolchain paths | Probes binary version/help; stages source bytes and writes immutable plan/run directory | `RUN_MANIFEST.json`, `RUN_STATE.json`, `COMMAND.sh`, HOLD states and preflight summary |
| `python mamey_run.py phylo-run ... --approved` | explicit genome list, HMM, outgroup and workdir | Executes GToTree/IQ-TREE, mandatory QC and optional requested fastANI; writes in workdir | `run_status.json`, process status, QC, alignment/tree/ANI files and logs |
| `tools/plan_gtotree_iqtree.py discover --run-dir ...` | exact planner run/output directory | Reads and hashes observed outputs; optional `--receipt` creates a new receipt | Unique alignment candidate and retained denominator; this is not tree inference |
| `tools/phylo_place.py report ...` | compatible jplace, reference package and metadata | Processes a graft, tables and optional graphics/caption | Actual attempt state and warnings; length or requested-metadata holds return 2, while optional diagnostic-figure/caption failures can coexist with zero |

A name such as `plan`, `dry-run` or `report` does not establish a read-only operation.
Keep paths printed by the selected command, rather than assuming every companion has
one universal directory layout. The planner's state and the executor's status are
separate files and must be reconciled explicitly.

## Bind resource settings and approval

`phylo-run` defaults to `--threads 4 --parallel 1`: 4 threads, one job at a time.
For a single-core genome run, specify `--threads 1 --parallel 1
--iqtree-threads 1` on `phylo-run`. Use a different budget only when it
matches the user's authorized plan. For a 16S preparation/placement run, bind the
explicit `--threads` value and expected tree workload separately.

The planner supports `--threads-per-tree` 1–4 within `--max-concurrent-cores` 1–4.
It records resource accounting; it does not launch a dispatcher or police unrelated
processes. The legacy direct-command recipe carries an approval comment. The current
governed 2.0.0 recipe instead delegates to `run_planned_tree.py --plan-dir`: that route
requires explicit `--approved`, a matching `RUN_STATE.json` with `approved=true`, and
bound runtime, input hashes/roster, labels, tools, HMM and resource settings. These
checks verify supplied records, not the identity of a human approver. Placement's
`--approved-by` remains a separate operator affirmation. Match actual authorization
and the selected route's bindings before running.

## MLSA inputs, completion and recovery

`build_mlsa.py` scans only immediate lowercase `*.fna` files. It resolves executables from `--bin-dir`, then `MAMEY_PHYLO_BIN` (or `PHYLO_BIN` when the former is unset), then PATH. Five seed files must exist. The public CLI now delegates to `tools/_mlsa_resources.py`, whose argparse interface rejects unknown options; the lower-level computational worker still reads its internal arguments manually. Supported controls include `--threads`, `--bin-dir`, `--seeds-dir`, `--native-work-root`, `--rss-limit-bytes`, `--min-free-disk-bytes`, `--timeout-seconds` and `--native-copy-limit-bytes`. Budgets must be finite and positive; byte budgets and threads must be integers. Default threads remain 4. The coordinator sets six native-thread environment variables to 1, binds source/seed/tool/interpreter hashes, admits resource estimates and watches the whole worker for RSS, disk and elapsed time. These controls do not establish a universal CPU ceiling or a successful biological workflow; inspect the actual resource receipt.

The seed-selected CDS is the highest-bitscore returned BLAST subject, not a reciprocal/coverage-thresholded orthology decision. Inspect `loci_report.tsv` and original selection evidence before calling it an ortholog. A locus with no hits across the panel is omitted; a taxon with at least one retained locus is kept with gaps in its missing partitions; a taxon missing all loci disappears from the supermatrix. Compare intended genomes, per-locus HIT/NO_HIT rows, actual partition count and retained tip roster before describing the result as a five-locus/full-pool screen. `_OUTGROUP` in a filename is just part of the escaped taxon label here: this command neither enforces one outgroup nor passes an outgroup/rooting option to IQ-TREE.

The output must be new or empty, with an existing parent, and must not overlap the genome, seed or code tree. The native-work root must also avoid protected inputs/output. Public preflight refusals normally return 4; parser/usage errors return 2. A monitored worker, completion or publication failure normally returns 6 and can leave diagnostics under `RESOURCE_ATTEMPT/<attempt-id>/`. Retain `REQUEST.json`, `RESOURCE.json`, `WORKER_COMPLETION.json`, terminal `SUCCEEDED.json`/`FAILED.json` and `worker.log` where produced. Some preflight failures occur before those artifacts exist. The lower-level worker has its own statuses, which are not the public wrapper's full exit contract. Preserve failed/partial attempts and use a fresh destination after diagnosis; output promotion is not a resumable multi-file transaction.

Public exit 0 requires a resource-admitted, monitored worker result, matching completion/output bindings, successful cleanup and promotion. The worker's final tree check remains existence/nonzero bytes; it does not parse leaf identity/support or enforce full-panel/five-locus coverage. No rendered figure or sign-off is produced. Keep the resource-attempt bindings alongside `taxon_map.tsv`, selection files and actual partitions/tips. Exact executable hashes are not tool-version validation, and mechanical completion is not orthology, taxonomy or scientific acceptance.

## Separate accepted versions from verified interfaces

The shared version policy accepts GToTree 1.8.19 and 2.0.x. Both planner and
runner use `tools/_gtotree_versions.py`: v1 requires/emits `-n`, while v2 omits it
and probes detailed help with `-s`. This repairs the earlier planner/runner option
mismatch. Version-family admission is still separate from source-specific resource
admission: unverified v2 runtime profiles remain held, and the governed 2.0.0 route
requires its exact runtime and plan bindings. Preserve the selected version, help,
resource contract, generated command and receipt rather than treating a recognized
version or a retired caveat as evidence of a completed run.

## Validate the requested outputs

A prepared FASTA is not a completed tree. A tree file is not a reviewed figure,
validated taxonomy or verified ANI result. `phylo_place.py report` returns 2 when
branch-length admission or requested metadata-strip completion is held. A failed
optional diagnostic render/caption or absent advisory sign-off helper need not
block zero. Inspect `<group>_REPORT_ATTEMPT.json`, requested artifacts and warnings.

For `phylo-run`, a requested fastANI stage must produce its current output and pass
its execution checks; typed failures preserve core-tree artifacts and return nonzero.
Retain comparison direction, raw matched/total fragments and aligned fraction. Missing
ANI rows are a state to diagnose, not measured zero. Neither an ANI threshold nor
placement within one reference panel automatically establishes a species name or novelty.

## Resolve scanner HMMs consistently

The HMM doctor entry and scanner share `mamey.wheelhouse.resolve_hmm_database`.
Resolution first accepts an existing `SM_HMM_DB` path (this branch checks existence, not regular-file type), then `MAMEY_HMM_DIR`, shared-root `hmm/`,
bundle-local 148 set, discovered add-on 148 set, then bundle-local 35 set. Directory
tiers prefer `scanner_pfam_150.hmm` over `scanner_pfam.hmm`. The filename's count is a
hint: validate actual content and record the selected hash. Provisioning does not
mean a scan ran or that the HMM file is valid.

The local PubMed corpus helper parses authorized PDF exports; it is not a network
retrieval client. See [external assets](EXTERNAL_ASSETS_GUIDE.md) for acquisition and
[external data](EXTERNAL_DATA.md) for its local input/output recipe.

## Source owners

- [Autopilot](../tools/phylo_autopilot.py): classification, routing, reference preparation and dry-run boundary.
- [MLSA builder](../tools/build_mlsa.py) and [resource coordinator](../tools/_mlsa_resources.py): five protein loci, public admission/monitoring, completion bindings and companion pipeline.
- [Planner](../tools/plan_gtotree_iqtree.py): immutable planner artifacts, resource accounting and generated commands.
- [Genome runner](../tools/run_planned_tree.py): version-specific commands, native status, QC and requested ANI.
- [CLI](../mamey/cli.py): public forwarding interface and resource defaults.
- [Placement](../tools/phylo_place.py): reference inference, output containment, reporting and advisory/render behavior.
- [Scanner resolver](../mamey/wheelhouse.py) and [external dataset resolver](../mamey/external_data.py): HMM provisioning.
