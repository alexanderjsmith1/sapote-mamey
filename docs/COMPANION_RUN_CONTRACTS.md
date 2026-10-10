# Companion run contracts for people and assistants

Source scope: Sapote-Mamey v9.7.447 / build 20261003v97447a. This guide describes
local code behavior. Use the current user request and existing matching authorization
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
| `tools/phylo_place.py report ...` | compatible jplace, reference package and metadata | Processes a graft, tables and optional graphics/caption | Actual artifacts and warnings; zero exit can coexist with missing/held graphics |

A name such as `plan`, `dry-run` or `report` does not establish a read-only operation.
Keep paths printed by the selected command, rather than assuming every companion has
one universal directory layout. The planner's state and the executor's status are
separate files and must be reconciled explicitly.

## Bind resource settings and approval

For the default one-core genome run, specify `--threads 1 --parallel 1
--iqtree-threads 1` on `phylo-run`. The .447 CLI and runner otherwise default to
four threads and two parallel GToTree jobs. Use a different budget only when it
matches the user's authorized plan. For a 16S preparation/placement run, bind the
explicit `--threads` value and expected tree workload separately.

The planner supports `--threads-per-tree` 1–4 within `--max-concurrent-cores` 1–4.
It records resource accounting; it does not launch a dispatcher or police other
processes. Its `COMMAND.sh` contains an approval comment but no code that reads
`RUN_STATE.json` before launching GToTree. The runner's `--approved` and placement's
`--approved-by` are operator affirmations, not authenticated approval records or
automatic imports of the planner manifest. Match selected inputs, paths, resources
and actual approval evidence before running.

## MLSA inputs, completion and recovery

`build_mlsa.py` scans only immediate lowercase `*.fna` files. It resolves executables from `--bin-dir`, then `MAMEY_PHYLO_BIN` (or `PHYLO_BIN` when the former is unset), then PATH, but does not probe/validate their versions. Five seed files must exist. Use the documented positional input/output and supported `--threads`, `--bin-dir`, `--seeds-dir` spelling; this driver manually reads arguments rather than rejecting every unknown option. Its default thread string is `4`, forwarded to BLASTp and IQ-TREE. MUSCLE receives no thread option from this driver, so `--threads 1` is not a verified whole-pipeline CPU ceiling; bind the actual selected tools' behavior to the authorized resource budget.

The seed-selected CDS is the highest-bitscore returned BLAST subject, not a reciprocal/coverage-thresholded orthology decision. Inspect `loci_report.tsv` and original selection evidence before calling it an ortholog. A locus with no hits across the panel is omitted; a taxon with at least one retained locus is kept with gaps in its missing partitions; a taxon missing all loci disappears from the supermatrix. Compare intended genomes, per-locus HIT/NO_HIT rows, actual partition count and retained tip roster before describing the result as a five-locus/full-pool screen. `_OUTGROUP` in a filename is just part of the escaped taxon label here: this command neither enforces one outgroup nor passes an outgroup/rooting option to IQ-TREE.

Output must be new or an existing empty nonsymlink directory; choose it outside source/code trees. Subdirectories/status/log and native outputs are written sequentially with no group rollback or resumable cache. Missing tools/seeds return 3; output/input-roster refusals return 4; caught pipeline failures record FAILED and return 6. Earlier setup/argument failures or interruption can leave no final status or an IN_PROGRESS/partial directory. Preserve it and captured diagnostics, resolve the cause, then use a fresh destination; do not reuse old native products as a completed retry.

Exit 0 with COMPLETE means invoked tools succeeded and selected checks passed. The final tree check is only existence/nonzero bytes; it does not parse leaf identity/support or enforce full-panel/five-locus coverage. No rendered figure or sign-off is produced. `taxon_map.tsv` retains input basenames, and status/log/selection files are not source/output hash manifests. Retain full genome/seed paths and hashes, binary/version bindings, arguments, partition/tip denominators and output hashes separately; tree review/taxonomy remain owner decisions.

## Separate accepted versions from verified interfaces

The shared version list accepts GToTree 1.8.19 and 2.0.x. That list is not a proof
that every command builder supports both. The .447 planner checks for `-n <int>`
and emits `-n` unconditionally; the runner's v2 branch deliberately omits `-n`.
Hold a v2 planner route for source/interface reconciliation when its local help
or command rejects that option. Do not clear a HOLD by changing its label.
Preserve version, help and generated command evidence for the owning code repair.

## Validate the requested outputs

A prepared FASTA is not a completed tree. A tree file is not a reviewed figure,
validated taxonomy or verified ANI result. `phylo_place.py report` may hold figures
when branch lengths remain unverified, skip a failed caption, or omit an advisory
sign-off helper while returning zero. Inspect every requested file and the warning
stream before recording task completion.

For `phylo-run`, a requested fastANI stage must produce its current output and pass
its execution checks; typed failures preserve core-tree artifacts and return nonzero.
Retain comparison direction, raw matched/total fragments and aligned fraction. Missing
ANI rows are a state to diagnose, not measured zero. Neither an ANI threshold nor
placement within one reference panel automatically establishes a species name or novelty.

## Resolve scanner HMMs consistently

The HMM doctor entry and scanner share `mamey.wheelhouse.resolve_hmm_database`.
Resolution is an existing `SM_HMM_DB` file, then `MAMEY_HMM_DIR`, shared-root `hmm/`,
bundle-local 148 set, discovered add-on 148 set, then bundle-local 35 set. Directory
tiers prefer `scanner_pfam_150.hmm` over `scanner_pfam.hmm`. The filename's count is a
hint: validate actual content and record the selected hash. Provisioning does not
mean a scan ran or that the HMM file is valid.

The local PubMed corpus helper parses authorized PDF exports; it is not a network
retrieval client. See [external assets](EXTERNAL_ASSETS_GUIDE.md) for acquisition and
[external data](EXTERNAL_DATA.md) for its local input/output recipe.

## Source owners

- [Autopilot](../tools/phylo_autopilot.py): classification, routing, reference preparation and dry-run boundary.
- [MLSA builder](../tools/build_mlsa.py): five protein loci and executed companion pipeline.
- [Planner](../tools/plan_gtotree_iqtree.py): immutable planner artifacts, resource accounting and generated commands.
- [Genome runner](../tools/run_planned_tree.py): version-specific commands, native status, QC and requested ANI.
- [CLI](../mamey/cli.py): public forwarding interface and resource defaults.
- [Placement](../tools/phylo_place.py): reference inference, output containment, reporting and advisory/render behavior.
- [Scanner resolver](../mamey/wheelhouse.py) and [external dataset resolver](../mamey/external_data.py): HMM provisioning.

These descriptions are source-derived documentation checks, not execution validation
of installed companion binaries or a full-suite pass.
