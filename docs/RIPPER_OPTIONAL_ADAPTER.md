# Optional RiPPER adapter — candidate

This standalone tool is an isolated development proposal based on Sapote–Mamey
v9.7.452 / engine 1.9.176 / build 20261016v97452a. It supports an explicitly
admitted native discovery route and retained-result inspection. It does not
submit network accessions, install dependencies, change core scores or ingest
a canonical package. Synthetic tests and the completed fabricated native smoke
are distinct validation evidence.

## Explicit local adaptation and lifecycle controls

The optional candidate now binds a separate lane05 adapted-source review profile,
streams explicitly budgeted model roles, and provides a bounded preflight and
opt-in self-authored synthetic stub supervisor. See
[operational lifecycle](RIPPER_OPERATIONAL_LIFECYCLE.md) for exact roles, caps,
statuses and limitations. Default preflight launches nothing. The [native discovery contract](RIPPER_NATIVE_DISCOVERY.md)
adds executable supervision after an exact concrete parent review; the current
header-adapted profile has completed one fabricated native raw-discovery run
with 78 candidates (`SUCCESS_UNBOUND`). HMM annotation and coordinate-producer
evidence remain separate; candidate membership is unverified. See
[CLI examples and Methods wording](RIPPER_CLI_METHODS.md).

## Current archived-source profile

The supplied original source archive now verifies a local GenBank entry point and
exact TSV headers. See [archived local contract](history/retired_458/RIPPER_ARCHIVED_LOCAL_CONTRACT.md)
for the pinned revision, verified hashes, single-record/query restriction, first-hit
selection, startup FTP side effect, dependency/license holds and strict optional
main/distant import profile. These findings supersede the earlier retrieval holds
below about unknown local input and headers. The original archived-source review itself did not execute upstream code; the
subsequent adapted native run is described above. Archived-source/container
equivalence remains unknown. The v2 import/member holds
remain mandatory.

## Earlier upstream identity and interface research

The intended project is **RiPPER (RiPP Precursor Peptide Enhanced Recognition)**,
linked by Santos-Aberturas et al., Nucleic Acids Research (2019),
[doi:10.1093/nar/gkz192](https://pmc.ncbi.nlm.nih.gov/articles/PMC6511847/).
It screens short coding candidates near selected tailoring enzymes; predictions
need biological validation. Paper defaults and benchmark results are not local
measurements. This differs from Cohen's rule-learning RIPPER algorithm in
[Fast Effective Rule Induction (1995)](https://www.sciencedirect.com/science/article/pii/B9781558603776500232).

Maintainer [ripdock documentation](https://hub.docker.com/r/streptomyces/ripdock/)
describes version 1.1 and recommends Docker; its documented recipe is
`docker pull streptomyces/ripdock`, then a container mounting the work directory
at the fixed container mount `/home/mnt`, not a personal home. This is the
archived wrapper's fixed path, not a configurable environment variable. Inside it,
`./ripper_run.sh /home/mnt/te_accessions.txt` consumes
one NCBI protein accession per line. RODEO/GenBank retrieval makes this a
network workflow. Dependencies listed are Perl ≥5.14, BioPerl, Python ≥2.7,
Biopython, DBI/DBD::SQLite, HMMER and modified Prodigal-short; Pfam and EGN are
also involved. Those historical minimums do not establish current compatibility.
Configuration is `local.conf`: flankLen 17500, minPPlen 20, maxPPlen 120,
maxDistFromTE 8000, sameStrandReward 5, fastaOutputLimit 3,
prodigalScoreThresh 7.5. Outputs include annotated GenBank, `out.txt`,
`distant.txt`, peptide FASTA and network products. A no-argument launcher uses
upstream test accessions, so it is not a harmless presence probe. No documented
arbitrary local-GenBank input contract was verified here.

The [retrievable master README](https://github.com/streptomyces/ripper/blob/master/README.md)
points to norodeodock, while the paper points to ripper/ripdock. GitHub root,
script and license retrieval failed or returned incomplete pages. No commit,
full image digest, authentic TSV headers, software license, current executable
availability or local scientific run was independently verified. The article's
CC BY license does not establish the software license. Do not vendor upstream
code or represent `latest` as a pinned dependency. No upstream code was copied.

## Local contract

Run `python tools/ripper_adapter.py --help` from an eventual integrated candidate,
using a verified Python ≥3.12 runtime. The core planner/importer uses the standard
library. Optional local-plan `--semantic-validation` uses lazily imported Biopython
for strict input binding; it still emits a held, nonexecuting plan. Core routes have no network, subprocess or baseline import. The opt-in semantic
route parses only bound local files with Biopython and reports a dependency HOLD
when that optional package is unavailable. CLI messages use standard logging; JSON file receipts are the
machine-readable outputs and refusal exit codes remain nonzero. Output must be a fresh directory outside its source tree.
It refuses occupied output directories and an output path that is itself a
symlink. Validation happens before output creation; a later filesystem write
failure can leave a partial directory, which must be retained and inspected.
Input files must be regular, non-symlink files, each ≤5 MiB. Inputs must remain
stable during admission; hashes are rechecked before publication. These checks
are not filesystem locks or authentication.

`plan --queries queries.json --out /absolute/fresh/plan` writes `PLAN.json` and
`enzyme_accessions.txt` only. Queries use schema `ripper-queries/1`, with
`queries` containing `enzyme_accession`, `strain`, `full_contig`, `region`, and
`bgc_alias`. One enzyme accession maps to one declared four-part query context.
Ambiguous/multiple mappings require a separately reconciled work order. Full
identifiers are preserved, never normalized. Identity is an operator declaration;
this adapter does not independently prove that the accession belongs to the locus.
Candidate records nest these values under `query_context` and retain the displayed
`query_identity`. They do not expose them as candidate `strain`, `full_contig`,
`region`, `bgc_alias` or `identity` fields. The enzyme's declared query context does
not establish the peptide's location or BGC membership. Every imported candidate
has `candidate_membership: UNVERIFIED` and
`attribution_status: HOLD_COORDINATE_ASSEMBLY_MAPPING`. This remains held until
authentic candidate coordinates and an assembly-bound mapping are reconciled.
No real locus attribution is admitted to a canonical package by this tool.
`PLAN.json` uses `ripper-plan/2`, `plan_status: PLANNED` and
`upstream_execution: NOT_EXECUTED`.

For one supplied TSV, run:

```text
python tools/ripper_adapter.py import \
  --queries queries.json --receipt run.json \
  --raw out.txt --columns columns.json --config local.conf \
  --completion-log completion.log --out /absolute/fresh/evidence
```

`columns.json` explicitly maps exactly `enzyme_accession`, `peptide_id`, and
`sequence` to observed TSV column names. Headers are not guessed because upstream
header bytes were not verified. TSV rows preserve all original fields and the
physical row number. Duplicate headers, ragged rows, unbound accessions, duplicate
query/peptide pairs and invalid amino acid strings fail closed. Only uppercase
20-residue amino acid sequences are admitted in this initial profile; ambiguous
residues, stops or alternative alphabets require review rather than silent edits.
No coordinates, score calibrations, cleavage sites or product labels are inferred.
A negative score is preserved rather than filtered: this adapter does not
reimplement upstream candidate selection.

A `ripper-run/1` receipt requires `upstream` equal to the verified project URL,
`evidence_kind` of `operator_supplied` or `synthetic_fixture`, a nonempty `reason`,
and `state` of `COMPLETE`, `FAILED`, `UNAVAILABLE` or `NOT_RUN`. COMPLETE additionally
requires integer `exit_code: 0`, exact `completed_accessions` matching the selected
query roster, `runtime_versions` with nonempty strings, and `upstream_revision`
as a 40-character commit hash or full `sha256:` image digest. Bind `raw_sha256`,
`config_sha256`, `completion_log_sha256`, `queries_sha256` and `columns_sha256`
to the exact supplied file bytes. Changing any query locus while retaining the
same accession list, or changing the column mapping, invalidates the receipt.
Reformatted bytes also require rebinding. These hashes bind declarations; they
do not establish genomic origin, candidate membership or execution authenticity. The all-zero
revision is allowed only for explicitly synthetic fixtures. Required fields are
visible declarations, not proof that upstream ran successfully. The adapter
hashes and retains the completion log's source locator; it does not interpret
arbitrary log formats or authenticate the operator.

For FAILED/UNAVAILABLE/NOT_RUN, supply only queries, receipt and output. Stale
raw rows cannot accompany those states. Candidate counts are null, never zero.
For an admitted declared COMPLETE input, synthetic assessments use
`SYNTHETIC_RETAINED_CANDIDATES` or `SYNTHETIC_NO_RETAINED_CANDIDATES`;
operator-supplied assessments use `OPERATOR_DECLARED_RETAINED_CANDIDATES` or
`OPERATOR_DECLARED_NO_RETAINED_CANDIDATES`. Noncomplete assessments qualify the
declared state with the same synthetic/operator provenance prefix. Each assessment
also carries `evidence_kind`, `upstream_execution`, `declared_upstream_state`,
`query_identity` and `query_context`. A no-retained-candidate result applies only to rows in
this selected TSV for these selected enzyme queries. It is not RiPP absence,
a complete genome screen, or proof that a separate `distant.txt` channel was
searched. Import distant output separately with its own bound receipt; this first
wave does not merge/deduplicate channels.

`RIPPER_EVIDENCE.json` now uses `ripper-evidence/2`. Its top-level `import_status`
is `ADMITTED_SYNTHETIC` or `ADMITTED_OPERATOR_DECLARATION`: this reports importer
admission, separately from `declared_upstream_state`. Top-level and per-row
`evidence_kind` distinguish fixture versus operator evidence. `upstream_execution`
is `NOT_EXECUTED_SYNTHETIC` for fixtures or `OPERATOR_DECLARED_UNATTESTED` for
operator declarations. A declared COMPLETE state never proves upstream execution.
CLI logging exposes import status, evidence kind, execution qualification and
declared upstream state together, so synthetic admission cannot appear as a live
completion. JSON preserves source paths, sizes/hashes, raw fields, declared query
context, completion/provenance declarations and the membership hold. The output
schema change deliberately removes the old ambiguous top-level `state` and copied
candidate `identity` fields; consumers must read the explicit version-2 fields. Original
inputs are read in place and remain required evidence: keep raw TSV, configuration,
query roster, mapping and logs beside their original checksum records. No source
copy or deletion is performed. A portable transfer must explicitly include those
inputs; JSON source paths alone are not a transferable raw-evidence archive.

## Integration holds and validation

Before a live route: admit a pinned source revision or full image digest,
verify software/dependency redistribution licenses, obtain representative authentic
`out.txt`/`distant.txt` and per-query completion logs, verify runtime/reference
versions and checksums (including Pfam and Prodigal-short build), and reconcile
accession-to-local-locus identity. Separately decide whether the documented remote
retrieval workflow is desired or a reviewed offline GenBank adaptation is needed.
No generic `ripper --version`, local-GBK launcher, exact upstream TSV schema or
automatic success detector is invented here.

Synthetic fixtures and `tests/test_ripper_adapter.py` exercise planning, hits,
scoped no-retained-candidate results, noncomplete evidence, source/identity/schema
refusals and output isolation. Follow-up tests cover changed locus/column receipt
bindings, unverified membership, synthetic/operator execution labels at every
level, CLI qualification and null counts for noncomplete states. They are not upstream compatibility tests or
biological sensitivity/specificity estimates. The all-zero fixture revision,
synthetic accessions and completion log explicitly denote **no live tool run**.
Core CLI, companion registry, workbooks, version metadata and generated manifests
are intentionally left for parent integration after these holds are resolved.
