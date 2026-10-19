# RiPPER native discovery: CLI and Methods

The optional adapter supports planning, exact source/runtime binding, supervised
native discovery, retained-result inspection and qualified coordinate evaluation.
Commands below use placeholders; set absolute paths to your admitted Python
environment, bundle and retained files. Output directories must be new and outside
the bundle source tree. A successful inspection is not permission for a new run.

## Inspect a retained native result

```sh
"$PYTHON" -B "$ADAPTER" native-result \
  --terminal "$RUN_ROOT/EXECUTION_TERMINAL.json" \
  --raw "$RUN_ROOT/RAW_DISCOVERY.json" \
  --control-result "$CONTROL_RESULT" \
  --out "$FRESH_INSPECTION_OUT"
```

`ADAPTER` is the absolute path to `tools/ripper_adapter.py`. `CONTROL_RESULT`
is the explicit outer-invocation control receipt for a legacy terminal. New
terminals use off-canonical serialization and exclusive canonical publication;
staging files are not terminal records. The inspector follows only files you
explicitly supply, not paths embedded in their contents. It checks terminal/raw
content consistency; it does not independently authenticate the original process
or revalidate every original input or native stage. Original receipts remain needed.

For the completed fabricated run, `NATIVE_RESULT.json` reports:

```json
{
  "terminal_status": "SUCCESS_UNBOUND",
  "raw_candidate_count": 78,
  "lexical_channel_counts": {"main": 3, "distant": 75},
  "hmm_annotation": "NOT_RUN_SEPARATE_STAGE",
  "coordinate_status": "ABSENT_PRODUCER_MAPPING",
  "candidate_membership": "UNVERIFIED",
  "canonical_import": "NOT_ADMITTED",
  "biological_absence_inferred": false
}
```

The main/distant labels are source serial-number channels. The 75 distant rows
are not 75 HMM-supported predictions. Distinct IDs sharing a sequence remain
distinct raw rows. `SUCCESS_UNBOUND` is preserved; it is not renamed to annotated,
coordinate verified, biologically validated or canonical.

To inspect a failed, interrupted or held terminal, omit `--raw`; the saved
inspection preserves the terminal state and a null candidate count, with exit
code 2. Stale raw rows supplied alongside an unadmitted terminal are refused.
For an admitted raw result, missing raw bytes, mismatched hashes/counts, changed
scientific qualifiers or a contradictory source declaration are refused. The exact
nine raw columns are required: strand and distance fields use integers, scores
must be finite numbers, and booleans cannot stand in for either. Extra HMM fields
cannot turn a raw row into an annotation.

## Prepare a new native run

Create an exact adapted-source profile with `adapted-profile`, an explicit
`ripper-lifecycle-spec/1` spec in mode `adapted_local05`, and all required
`--file ROLE=PATH` bindings. Run `lifecycle` without `--execute-native` first:

```sh
"$PYTHON" -B "$ADAPTER" lifecycle \
  --spec "$SPEC" --adapted-profile "$ADAPTED_PROFILE" \
  --run-root "$FRESH_RUN_ROOT" \
  --file "archived_base=$ORIGINAL_SOURCE" \
  --file "source_patch=$CUMULATIVE_PATCH" \
  --file "upstream_source=$ADAPTED_SOURCE" \
  --file "adaptation_receipt=$SOURCE_OWNER_RECEIPT" \
  --file "source_closure=$SOURCE_HANDOFF" \
  --file "source_discovery_contract=$DISCOVERY_CONTRACT"
```

The shown roles illustrate source admission; also supply every input, executable,
module and runtime role in the spec. Incomplete roles produce a recorded HOLD.
A matching complete preflight writes the concrete native review request. It does
not launch RiPPER. Review its exact source/profile/spec/file/argv/environment and
semantic bindings before creating a matching execution admission.

For a separately admitted new run, use the same spec/profile/files/root and add
`--execute-native --native-admission "$ADMISSION" --resume-preflight` to resume
its pristine preflight. The supervisor verifies all exact bindings and records
execution, cleanup and terminal status. The completed fabricated run's one-run
scope is consumed; its admission/root cannot authorize a retry. Staging aliases
of a pristine preflight are preserved and validated.

## Keep result stages separate

| Recorded result | Supported interpretation | Next evidence needed |
|---|---|---|
| `SUCCESS_UNBOUND` | Retained raw candidates in the declared discovery scope | Separately admitted annotation or coordinate evidence for those tasks |
| `NO_HIT` | No tailoring-enzyme hit declared for the bound query/record | Exact completion/stage evidence; no biological absence inference |
| `NO_RETAINED_CANDIDATES` | Enzyme match with no retained raw candidates | Preserve that distinction from no enzyme hit |
| `FAILED`, `INTERRUPTED`, `HOLD`, `AMBIGUOUS` | Result not admitted; candidate count null | Resolve the recorded cause; retain prior evidence |
| Direct coordinate/sequence match | Declared interval translates consistently | Producer provenance and independent BGC attribution remain separate |

Nine-column raw SQLite/JSON and an empty discovery summary do not satisfy the
eleven-column merged annotation import. The `import` command needs a separately
produced annotated table and its matching complete receipt, columns, configuration,
completion log and query coverage. Do not convert raw native JSON into an operator
receipt to bypass this boundary.

## Evaluate native coordinate reconstruction

`native-coordinates` consumes a `ripper-native-coordinate-reconstruction/1` packet
and an explicit roster of its 18 bound artifact roles. It does not relabel native
raw JSON as a merged operator or synthetic result. Review the packet and prepare
a separate JSON object mapping each required role to its exact absolute file path.
The command compares that explicit roster against the packet; it does not follow
additional paths embedded in packet metadata.

```sh
"$PYTHON" -B - "$ADAPTER" "$COORD_PACKET" "$COORD_INPUTS" \
  "$CONTROL_RESULT" "$FRESH_COORD_OUT" <<'PY'
import json, runpy, sys
adapter, packet, inputs, control, out = sys.argv[1:]
with open(inputs, encoding="utf-8") as handle:
    roles = json.load(handle)
args = ["native-coordinates", "--packet", packet, "--control-result", control,
        "--out", out]
for role, path in sorted(roles.items()):
    args += ["--file", role + "=" + path]
sys.argv = [adapter, *args]
runpy.run_path(adapter, run_name="__main__")
PY
```

Required roles are `raw`, `terminal`, `faa`, `score`, `window`, `genbank`, `query`,
`stage`, `provenance`, `source`, `config`, `reconstruction`, `profile`, `queries`,
`sqlite`, `exported_genbank`, `prodigal_stage_started` and `lifecycle_launch`. All
are bounded regular inputs. The outer control receipt is also explicit for legacy
terminal publication. The result is `NATIVE_COORDINATE_BINDING.json`.

The consumer joins canonical candidate IDs and raw SQLite row hashes to the
FASTA sequence and complete header, a unique matching 13-column Prodigal score
row, and the bound original record/window. It checks source-record identifiers
without stripping accession versions, original versus local interval conventions,
strand, selected tailoring-enzyme CDS, and translation. Candidate translation uses
the source's table-1 peptide policy; the selected CDS and Prodigal scoring model
can declare table 11. Terminal-stop removal and initial V/L-to-M correction alter
the amino-acid representation only. Nontriplet intervals are refused, not trimmed.

For the completed fabricated output, all 78 rows evaluate as
`RECONSTRUCTED_SEQUENCE_COORDINATES_UNATTESTED`, preserving
`evidence_kind=local_adapter_observed_native` and the recorded native execution.
The coordinate origin is `derived_from_retained_native_artifacts`; direct
instrumented producer evidence remains absent. The original raw JSON is unchanged
and still records `ABSENT_PRODUCER_MAPPING`. BGC membership remains `UNVERIFIED`,
HMM annotation remains `NOT_RUN_SEPARATE_STAGE`, and canonical import is not
admitted. These are usable reconstructed intervals with explicit provenance limits.

Wrong source/window bindings, version aliases, one-base offsets, reversed strands,
noninteger geometry, changed row/header hashes, duplicate candidate identities,
ambiguous score-row joins and promoted producer/HMM/BGC claims are refused.
Distinct IDs sharing sequence or geometry are not silently deduplicated.

## Methods wording for the completed fabricated smoke

A Sapote–Mamey v9.7.452-based development adapter supervised one native run of a
local RiPPER adaptation on a fabricated 6000-nt GenBank record with a 150-aa bait
exactly matching the selected source CDS. The executed source SHA256 was
`0b92227d09bb033074ec70379ef27c4767e2ab30c7e478e76e71c3abc13be0f3`;
its source profile was `local05-552e784c90c646d2`. The adaptation recognized the
exact native Prodigal score header while retaining the prior numeric/filter logic.
The run used Python 3.12.14, Biopython 1.88, Perl 5.34.1, BioPerl 1.7.8, BLAST+
2.17.0+, and a private arm64 modified Prodigal 2.6.3 build from pinned commit
`004218fbeb2cf54fe12d88ec2eede6a27d70ebf7`. Executable, module, configuration,
input, profile, source and stage hashes were retained in the run receipts.

The supervised limits were 300 s, 1 GiB sampled process-tree RSS, 256 MiB run
output and one compute thread. Sampling is not an OS quota. The process exited
0, cleanup uncertainty was false, and the raw consumer retained 78 candidates
(3 main and 75 distant serial-number rows). The result was `SUCCESS_UNBOUND`.
All 191 observed transitive file bindings matched before and after execution;
this did not establish an exhaustive OS or late-load dependency closure. An
independent retained-byte reparse confirmed the candidate, stage and source-
declaration consistency. HMM annotation was not run, candidate BGC membership
was unverified, and direct instrumented coordinate-producer evidence was absent.
This smoke established execution and raw-output compatibility for the fabricated
input; it did not measure biological sensitivity or precursor validity.

The actual run used the execution-manifest adapter hashes. Later inspection/publication
changes are development follow-ons and must not be credited as code that executed
that run. Preserve the exact execution terminal, raw discovery JSON, SQLite, FASTA,
source-stage outputs and before/after dependency receipts for reproducibility.

A separate read-only follow-on reconstructed and evaluated intervals for all 78
retained rows using source/window, FASTA/header, score-row and translation
consistency. It preserved native execution provenance and labelled the coordinate
evidence as retained-artifact reconstruction with no instrumented producer
attestation. The coordinate consumer did not rerun discovery, perform HMM
annotation or establish BGC membership.
