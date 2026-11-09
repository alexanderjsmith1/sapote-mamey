# CORASON: optional locus comparison against public genomes

`tools/corason_adapter.py` compares one locus against public genomes with CORASON, an external program that searches for related gene neighborhoods and builds a gene tree. The adapter has three subcommands: `plan`, `run` and `read`.

This is an optional, maintainer-level route. Most readers do not need it. It needs a reviewed external install and hand-written review files, and no tool in the bundle writes them for you.

**Quick check that the adapter works (about a second).** From the bundle root:

```bash
d=$(mktemp -d)
echo '{}' > "$d/empty.json"
python tools/corason_adapter.py plan --intake "$d/empty.json" --selection "$d/empty.json" \
  --runtime-manifest "$d/empty.json" --native-work-root "$d/cwork" \
  --write-root "$d/cout" --out "$d/cout/plan1"
```

The first two lines create a new scratch folder and an empty JSON file in it. Nothing else is
written. Success looks like `CORASON refused: INTAKE_SCHEMA`, exit code 2, and no `cout` folder
inside `$d`. The adapter is present and refuses incomplete input. A real plan needs the five files below.

- It is off by default. Core extraction, scores, packages and the antiSMASH-only figures never call it.
- It installs and downloads nothing. CORASON, its Perl and BLAST dependencies and their versions stay outside the bundle. The adapter refuses to run until you have reviewed and recorded them.
- Everything it writes is marked PRIVATE, even when the inputs are public. Publishing a result needs its own review.
- It supports no claim about compound identity, production, activity, species, novelty or physical adjacency of contigs.

## Prerequisites

Check these before you write any file. A run is refused if one fails.

- **Host.** At least 12 CPUs, as reported by the operating system. The pinned CORASON source asks BLAST for 12 threads. A 10-CPU laptop is refused, and there is no override.
- **Limits the run enforces.** 3.8 GB resident memory, 1800 seconds for the whole run, and 2 GB free disk on both the output folder and the work folder. Runs are one at a time, in the foreground, at low priority.
- **External source.** The original CORASON checkout at commit `aa70dddebafb210445794fd24b1c6b2e4177c58c` (AGPL-3.0), laid out as `<source_root>/CORASON/<helper>.pl`. All 28 helper scripts must match their pinned Git hashes. This is the original `nselem/corason` code, not a fork.
- **External tools.** `blastp`, `makeblastdb`, `muscle`, `Gblocks`, `FastTree`, `nw_topology`, `nw_display` and `nw_labels`, each with a recorded version probe.
- **Paths.** The work folder must exist and its path must contain no spaces or shell-special characters. Outputs need fresh folders. Existing ones are refused. There is no resume.
- **Input.** Finished Mamey packages built from public genome archives, with a reviewed public-source record and a package-validation record for each.

## The five input files

Every file is a JSON object. A hash is a lowercase SHA-256 string. A file binding is `{"path": ..., "bytes": ..., "sha256": ...}`. The review records are your own evidence. They are not certificates, and nothing in them grants permission to run.

**1. Intake** (`corason.public-intake.v1`): one record per package.

```json
{
  "schema": "corason.public-intake.v1",
  "records": [{
    "package": "/work/runs/EXAMPLE/package",
    "package_manifest_sha256": "<sha256 of manifest.json>",
    "source_zip": "<antiSMASH archive name>",
    "source_zip_sha256": "<sha256>",
    "source_bytes": 123456789,
    "public_receipt": {"path": "/work/review/public.json", "bytes": 800, "sha256": "<sha256>"},
    "validation_receipt": {"path": "/work/review/validation.json", "bytes": 700, "sha256": "<sha256>"}
  }]
}
```

The package manifest must list each locus with strain, full contig, node ID, region, BGC alias, start, end and source GBK. The archive hash must match the package. A locus in a raw ZIP with no package is held. Identities are case and version sensitive. The adapter does not shorten them.

**2. Public receipt** (`corason.public-source-review.v1`): ties the archive to its public records.

```json
{
  "schema": "corason.public-source-review.v1",
  "state": "REVIEWED_PUBLIC_SOURCE_BINDING",
  "scope": "PRIMARY_PUBLIC_SOURCE_BINDING",
  "source_zip_sha256": "<sha256>",
  "accession_versions": ["EXAMPLE01000001.1"],
  "primary_sources": [{
    "url": "https://eutils.ncbi.nlm.nih.gov/...",
    "accession_version": "EXAMPLE01000001.1",
    "metadata_sha256": "<sha256>"
  }]
}
```

The URLs must be HTTPS on an NCBI or ENA host. Every locus's full contig must appear in `accession_versions`. A folder name or taxon match is not enough. Accession metadata alone does not show that the sequence bytes match.

**3. Validation receipt** (`corason.package-validation-review.v1`): keeps the real validator output.

```json
{
  "schema": "corason.package-validation-review.v1",
  "state": "VALIDATED",
  "scope": "ACTUAL_PACKAGE_VALIDATION",
  "package_tree_sha256": "<package tree hash, see below>",
  "evidence_path": "/work/review/validate.log",
  "evidence_sha256": "<sha256 of that log>"
}
```

Validate first, on a working copy you are allowed to change. `python mamey_run.py validate <package>` rewrites `package_status.json` inside the package, and the tree hash covers that file. Save the validate output to the log named in `evidence_path`. Then compute the hash.

The package tree hash is the SHA-256 of one line per package file, in sorted path order: `relative/path`, a tab, that file's SHA-256, a newline. No command prints it. From the bundle root, this does (the path is your package folder):

```bash
python -c "from mamey.postseal_output import package_binding as b; print(b('runs/EXAMPLE/package')['package_tree_sha256'])"
```

It prints one 64-character hash. If the hash differs from the one in the receipt, `plan` stops with `PACKAGE_VALIDATION_UNBOUND`.

**4. Selection** (`corason.selection.v1`): which loci to compare, fixed before you see results.

```json
{
  "schema": "corason.selection.v1",
  "loci": ["EXAMPLE / <full contig> / region001 / BGC001"],
  "query": {
    "exact_locus": "EXAMPLE / <full contig> / region001 / BGC001",
    "locus_tag": "EXAMPLE_00010",
    "translation_sha256": "<sha256 of the saved CDS translation>"
  }
}
```

`loci` is an ordered list with no repeats, and every entry must come from the intake. The query must be one of them. Loci you leave out stay in the denominator. The adapter does not optimize the query, fetch references, predict genes or retranslate.

**5. Runtime** (`corason.runtime.v1`): records the external install you reviewed. It has `profile` set to `corason-original-aa70ddde-region-v1`, `kind` set to `NATIVE`, a `review_receipt` file binding, and an `identity` object. The review receipt (`corason.runtime-review.v1`, state `REVIEWED`) must carry `intent` equal to the runtime `kind` (`NATIVE`) and the exact hash of that identity object; otherwise the plan refuses with `RUNTIME_NOT_REVIEWED` (`tools/corason_adapter.py:251-254`). The identity holds:

- `commit`, `source_root`, `helpers` (each helper filename mapped to a file binding) and `entry` (the `corason.pl` binding);
- `interpreter` and `observer_python` file bindings, `architecture`, `perl_modules_reviewed` and `transitive_io_reviewed` set to true, an `environment_receipt` binding, and an explicit `environment` with `PATH`;
- `tools`: for each tool above, a `file` binding, a `probe` argv (a list of strings), `reported_version`, `probe_stdout_sha256` and `probe_stderr_sha256`;
- `entry_help_stdout_sha256`, and `prefilter_observer` set to `ReadingInputs-before-deletion-v1`;
- `resources`: `source_reviewed`, `prefilter_stage_reviewed`, `parallel_runs` of 1, `cpu_total` (12 or more, and no more than the host has), `effective_tool_threads` for every tool (BLAST at 12 or more), and `max_concurrent_children`. The largest tool thread count times `max_concurrent_children` must not exceed `cpu_total`.

The review receipt's `identity_sha256` is the SHA-256 of the identity object written as JSON with keys sorted and no spaces after separators. Its `observer_sha256` must equal the SHA-256 of the adapter's built-in observer script. Both print from the bundle root:

```bash
python -c "import sys,hashlib,json; sys.path.insert(0,'tools'); import corason_adapter as c; print(hashlib.sha256(c.observer_source().encode()).hexdigest()); print(c.content_digest(json.load(open('runtime.json'))['identity']))"
```

The first line is `observer_sha256`. The second is `identity_sha256`. Write them into the review receipt, then add the receipt's file binding to `runtime.json`. If you edit the identity again, recompute the second hash.

In `environment`, set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, `OMP_THREAD_LIMIT` and `PYTHONDONTWRITEBYTECODE` to the string `1`. These do not lower BLAST's own thread arguments. Names starting with `CORASON_` are reserved.

## Run it

```bash
python tools/corason_adapter.py plan --intake intake.json --selection selection.json \
  --runtime-manifest runtime.json --native-work-root /private/tmp/corason_work \
  --write-root /work/corason_out --out /work/corason_out/plan1
python tools/corason_adapter.py run --plan /work/corason_out/plan1/PLAN.json \
  --write-root /work/corason_out --out /work/corason_out/attempt1 --approved
python tools/corason_adapter.py read --run-receipt /work/corason_out/attempt1/RUN_STATE.json \
  --write-root /work/corason_out --out /work/corason_out/export1
```

`--read-only-root` is optional on `plan`. It names folders that must stay untouched.

**plan** reads metadata and hashes only. It runs no program and extracts no sequence. On success it writes `PLAN.json` and `COMMAND.sh`. `COMMAND.sh` just exits with an error. It is a stub, not a shortcut. A missing or unreviewed record stops `plan` before any output folder exists.

**run** needs `--approved`. Passing the flag is your statement that you reviewed the plan. Nothing in the files can approve it for you. It:

1. checks the runtime before launching anything;
2. re-derives the selection from the original archives;
3. stages only the selected loci and the query translation, and converts them with CORASON's `gbkIndex.pl`;
4. runs `corason.pl` with the source defaults (e-value 1E-15, bitscore 0, cluster radius 10, cluster e-value 1E-3, core e-value 1E-3, rescale 85000).

These defaults are the source's own values, not tuned choices. Biopython is loaded only for the conversion step. Fuzzy or compound CDS geometry, a missing or duplicate tag, several translations, or an internal stop all stop the run. One terminal stop codon may be removed, and both hashes are recorded. Any witnessed tool that fails stops the run, even when CORASON's own exit code hides it.

A good run ends with `RUN_STATE.json` showing status `COMPLETE_SCOPED_EVIDENCE`, plus `RUN_MANIFEST.json`, `SELECTED_RESULT.json` and `WHOLE_WORKER_ADMISSION.json`. A failed run keeps `WORKER_STATE`, `WHOLE_WORKER.log`, `EVENTS` and the phase logs, with no admission file. Do not read a failed folder as a result. Keep it, and retry into a new folder.

**read** checks the run against the original sources, rebuilds the result without launching any external program, and writes `EVIDENCE.json`, `loci.tsv`, `neighborhoods.tsv`, `leaf_crosswalk.tsv`, `HANDOFF.md` and `EXPORT_BINDINGS.json` into a new folder. A package is never changed. Use `EVIDENCE.json` for machine joins. Spreadsheet cells that start with a formula character get a leading apostrophe in the TSV files. Do not strip it from identities.

## Read the result

The route is in the `route` field of `EVIDENCE.json` and on the `Route:` line of `HANDOFF.md`.

| Route | What it means | Goal |
|---|---|---|
| `MULTILOCUS_CORE` | More than one verified core gene, at least two neighborhoods, and a complete matrix, tree and order. | `MET_STRUCTURAL_ONLY` |
| `QUERY_ONLY_SHAVED` | A bound query alignment and tree, with at least two neighborhoods. | `NOT_MET` |
| `QUERY_ONLY_UNSHAVED` | A bound query alignment and tree before shaving. | `NOT_MET` |
| `BLAST_ORDER` | Neighborhoods and the BLAST-order branch only. The tree is `NOT_ASSESSED`. | `NOT_MET` |
| anything incomplete or conflicting | `FAILED` or `HOLD`. | none |

`COMPLETE_SCOPED_EVIDENCE` means the export was verified. It does not mean the multilocus goal was reached. `MET_STRUCTURAL_ONLY` means the files fit together. It is not a test of orthology, alignment or tree accuracy.

The raw native SVG is `RAW_NATIVE_SVG_NOT_VISUALLY_ADMITTED`. No polished figure is promised. Absent output is not a no-hit. A no-hit needs a saved, successful search with the exact source gene membership. A failed conversion stops the attempt. It never drops a problem source and calls a smaller run complete.

Report the denominators with any result: source loci, selected and unselected loci, converted CDS, loci with a query hit, neighborhoods before and after filtering, and tree tips.

## Limits

- File hashes show that content is unchanged. They are not signed attestation. They do not protect against someone who edits every receipt.
- A process monitor watches memory and time. It is not a sandbox.
- Test runs use synthetic placeholder data and the kinds `SYNTHETIC_PROTOCOL_TEST` and result tag `SYNTHETIC_PROTOCOL_ONLY`. They check the protocol only. A native run has not been shown to work on any particular computer until the whole chain has been run there.
- Do not choose favorable queries or tune thresholds after you see results.
- The optional registry entry for CORASON reports "not probed". It never checks for an installed copy, so it cannot tell you the runtime is ready.

Sources: the [original code](https://github.com/nselem/corason/tree/aa70dddebafb210445794fd24b1c6b2e4177c58c) and [Navarro-Muñoz et al. (2020)](https://doi.org/10.1038/s41589-019-0400-9). For where CORASON sits among the companion tools, see [companion tools](companion_tools.md).
