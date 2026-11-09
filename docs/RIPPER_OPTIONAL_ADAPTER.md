# Optional RiPPER adapter

For maintainers. Skip this page unless you run RiPPER on a named strain. Core runs never need it.

RiPPER (RiPP Precursor Peptide Enhanced Recognition; Santos-Aberturas et al., Nucleic Acids Research
2019, [doi:10.1093/nar/gkz192](https://pmc.ncbi.nlm.nih.gov/articles/PMC6511847/)) searches near
selected tailoring enzymes for short ribosomally synthesized and post-translationally modified peptide
(RiPP) precursor candidates. A candidate is a lead for review. It is not a product, and a prediction
needs biological validation.

The adapter is a set of standalone scripts, `tools/ripper_*`. `mamey_run.py` has no RiPPER command.
The adapter does not fetch accessions, install dependencies, change core scores or write into a
package.

## Choose a route

| You have | Route | Page |
|---|---|---|
| A local GenBank record and a reviewed, locally adapted RiPPER source | Native discovery: the adapter runs the adapted source under a supervisor and keeps the raw candidate rows | [Native discovery](RIPPER_NATIVE_DISCOVERY.md), [commands](RIPPER_CLI_METHODS.md), [lifecycle](RIPPER_OPERATIONAL_LIFECYCLE.md) |
| A native run you already kept | Inspect it and check candidate coordinates | `native-result`, `native-coordinates` in the [commands page](RIPPER_CLI_METHODS.md) |
| Results from the upstream tool, run elsewhere | Import them with a receipt, below | This page |
| Only a plan | Write the plan and accession list; nothing runs | `plan`, below |

Native raw rows carry no annotation and no genome coordinates, and candidate membership stays
`UNVERIFIED`. Neither route sends anything into canonical scores.

## Subcommands

`python tools/ripper_adapter.py <subcommand> --help` lists the options of each.

| Subcommand | Purpose |
|---|---|
| `plan` | Write a plan and accession list. Nothing runs. |
| `source-profile` | Export the archived output-column contract. |
| `local-plan` | Hold-only plan for a local GenBank input. |
| `adapted-profile` | Bind the adapted base, patch and postimage files. |
| `bind-run` | Bind file-role digests. Not proof of readiness. |
| `lifecycle` | Bounded preflight; native or stub run only by explicit opt-in. |
| `lifecycle-batch` | One roster of record and bait pairs, with receipts per pair. |
| `native-result` | Inspect retained native terminal and raw bytes. |
| `native-coordinates` | Evaluate a native reconstruction packet. |
| `bind-coordinates` | Evaluate bound coordinate declarations. |
| `import` | Admit operator-supplied rows, or an unavailable, failed or not-run state. |

## Rules for every subcommand

- Use Python 3.12 or newer. The planner and importer use only the standard library. The optional
  `--semantic-validation` of `local-plan` needs Biopython and reports a hold if it is missing.
- The output folder must be new and outside the source tree. The tool refuses an existing folder
  and a symlinked output path. The one exception is a reviewed native run with `--resume-preflight`: it reuses the run root that its own earlier preflight reserved, and only when that folder is pristine and its source, files, profile, root and review request still match (see [native discovery](RIPPER_NATIVE_DISCOVERY.md)). No other existing folder is accepted. It validates before it writes; if a later write fails, keep the
  partial folder and inspect it.
- Inputs must be regular files, not symlinks, each at most 5 MiB by default. In `lifecycle`, model and
  executable roles can use larger streamed budgets and timeouts set in the spec; see
  [the lifecycle page](RIPPER_OPERATIONAL_LIFECYCLE.md). Hashes are rechecked before output
  is published.
- A refusal exits nonzero and names the reason in the message.

## Plan

`queries.json` lists the enzymes to search near. Each row declares the four-part locus identity
that the enzyme belongs to, written in full and never normalized:

```json
{
  "schema_version": "ripper-queries/1",
  "queries": [
    {"enzyme_accession": "WP_000000001.1", "strain": "STRAIN", "full_contig": "FULL_CONTIG_NAME",
     "region": "REGION", "bgc_alias": "BGC_ALIAS"}
  ]
}
```

One enzyme accession maps to one declared context. The adapter does not prove the accession
belongs to that locus.

```bash
python tools/ripper_adapter.py plan --queries queries.json --out /absolute/fresh/plan
```

Success is exit 0 and two files: `PLAN.json` (`ripper-plan/2`, `plan_status` `PLANNED`,
`upstream_execution` `NOT_EXECUTED`) and `enzyme_accessions.txt`, one accession per line.

For reference, the upstream container recipe runs `./ripper_run.sh /home/mnt/te_accessions.txt`,
which reads one protein accession per line from a fixed container mount. It retrieves records over
the network, so it is not the local route above.

## Import results from a run elsewhere

Use this when someone ran the upstream tool and you hold its tab-separated output. You supply the
queries, a run receipt, the raw table, a column map, the configuration and the completion log.

```bash
python tools/ripper_adapter.py import \
  --queries queries.json --receipt run.json \
  --raw out.txt --columns columns.json --config local.conf \
  --completion-log completion.log --out /absolute/fresh/evidence
```

`columns.json` maps exactly three keys, `enzyme_accession`, `peptide_id` and `sequence`, to three
different column names in the table. Headers are never guessed.

`run.json` is the receipt. It declares what happened and binds the files:

```json
{
  "schema_version": "ripper-run/1",
  "upstream": "https://github.com/streptomyces/ripper",
  "evidence_kind": "operator_supplied",
  "state": "COMPLETE",
  "reason": "why this run was made",
  "exit_code": 0,
  "completed_accessions": ["WP_000000001.1"],
  "runtime_versions": {"perl": "5.x"},
  "upstream_revision": "<40-character commit hash or sha256:<image digest>>",
  "queries_sha256": "...", "raw_sha256": "...", "config_sha256": "...",
  "completion_log_sha256": "...", "columns_sha256": "..."
}
```

- `evidence_kind` is `operator_supplied` or `synthetic_fixture`. An all-zero revision is allowed
  only for a synthetic fixture.
- `state` is one of `COMPLETE`, `FAILED`, `UNAVAILABLE`, `NOT_RUN`, `MISSING` or `INTERRUPTED`.
  Only `COMPLETE` takes the exit code, accession list, versions, revision and the five hashes.
  For any other state, supply only `--queries`, `--receipt` and `--out`.
- `completed_accessions` must match the query roster exactly. Each hash must equal the SHA-256 of
  the exact bytes you pass. Changing a query locus or the column map invalidates the receipt.

Rows are kept with all original fields and their row number. Duplicate headers, ragged rows,
unbound accessions, duplicate query and peptide pairs, and sequences with any character other
than the 20 uppercase amino-acid letters fail closed. Nothing is inferred: no coordinates, cleavage
sites, score calibration or product labels. A negative score is kept.

The hashes bind your declarations to your files. They do not show where the genome came from,
that a candidate sits in the BGC, or that the upstream tool really ran.

## What the output says

`RIPPER_EVIDENCE.json` uses `ripper-evidence/2`.

- `import_status` is `ADMITTED_SYNTHETIC` or `ADMITTED_OPERATOR_DECLARATION`. It reports that the
  importer admitted the files, not that the tool ran.
- `evidence_kind` and `upstream_execution` repeat on the top level and on every row. The latter is
  `NOT_EXECUTED_SYNTHETIC` or `OPERATOR_DECLARED_UNATTESTED`. A declared `COMPLETE` never proves execution.
- Every candidate has `candidate_membership` `UNVERIFIED` and `attribution_status`
  `HOLD_COORDINATE_ASSEMBLY_MAPPING`. Enzyme context sits under `query_context` and `query_identity`
  on the candidate, not as `strain` or `identity` fields.
- Candidate counts for `FAILED`, `UNAVAILABLE` and `NOT_RUN` are null, never zero.
- A complete run with no rows reads `OPERATOR_DECLARED_NO_RETAINED_CANDIDATES` (or `SYNTHETIC_`).
  That covers this table and these enzymes only. It is not evidence that the strain has no RiPPs.
  The separate `distant.txt` channel needs its own import and receipt; channels are not merged.

Keep the raw table, configuration, queries, column map and logs beside their checksums. The JSON
records source paths and hashes, not the files themselves.

## Before a live route

A route that runs the upstream tool on real data needs, in place:

- a pinned source revision or full image digest, and a software licence check;
- representative real `out.txt` and `distant.txt` and a completion log per query;
- recorded runtime and reference versions and checksums, including the Pfam and Prodigal-short builds;
- a reconciled link from each accession to its local locus.

The adapter provides no `ripper --version` probe, no generic local-GenBank launcher and no
automatic success detector. Tests in `tests/test_ripper_*.py` use synthetic fixtures. They check the
adapter's refusals and labels, not upstream compatibility or biological sensitivity.
