# RiPPER outcome and run-binding limits

A missing artifact is not a negative result. A missing/unreadable required file
refuses import with exit2 and no published evidence. An explicit MISSING receipt
can record known absence of evidence; INTERRUPTED records declared interruption.
FAILED, UNAVAILABLE and NOT_RUN remain separate. All noncomplete states have null
candidate counts and reject accompanying stale raw outputs. No state proves that
an upstream process ran; synthetic/operator execution qualifications remain explicit.

For declared COMPLETE, empty/headerless TSV refuses. A valid header-only TSV with
exact bound inputs and declared full query coverage is NO_RETAINED_ROWS_DECLARED_SCOPE,
not RiPP absence, a genome-wide screen, or completion of a separate distant channel.
Retained rows are RETAINED_CANDIDATES_UNBOUND until separately evaluated for local
coordinate consistency, and even direct sequence matches do not establish BGC
membership. `biological_absence_inferred` is always false. Unsupported arbitrary
outcome labels refuse rather than silently becoming successful/no-hit output.

Raw/config/query/column/log hashes and query coverage bind supplied declarations;
they do not authenticate process completion or timestamp freshness. Changing a
file without rebinding the receipt refuses. Reusing a coherent historic receipt
and all its identical inputs remains historical operator-supplied evidence, not
proof of a new run. A stricter optional run-binding boundary is described as it
is implemented; no source install, run, model readiness or upstream success follows
from import admission alone.


## Optional exact run boundary

`bind-run --manifest manifest.json --file role=/explicit/path ... --out /fresh/run`
reads a ripper-run-binding-manifest/1 with run_id, evidence_kind, profile_id,
source_revision and files{role:sha256}. Each role must be provided explicitly on
CLI; paths embedded in an artifact are never silently discovered/read. Original
archived source bytes must match the profile for operator-supplied bindings;
synthetic files are labeled SYNTHETIC_SOURCE_NOT_UPSTREAM. Adapted upstream source
needs separate profile admission with lane05/parent; it cannot pretend to be original.

Required complete roles: upstream_source, config, genbank, query_fasta, pfam_model,
ripp_model, completion_log, raw_output, queries and columns. Missing roles yield a
HOLD artifact. All supplied files retain exact path/size/SHA-256. Small JSON/text
inputs keep the 5 MiB per-file cap. Model/index roles use that route unless an
explicit `model_byte_budget` selects streaming (positive integer, at most 16 GiB),
with `hash_timeout_seconds` (positive finite seconds, default 30, at most 600).
Executable roles retain the 16 MiB legacy default or use an explicit
`executable_byte_budget` (positive integer, at most 512 MiB), with
`executable_hash_timeout_seconds` (positive finite seconds, default 30, at most 300).
A non-default `executable_hash_timeout_seconds` requires an explicit
`executable_byte_budget`; the legacy route uses 30 seconds.
These are per-file streaming limits, not an aggregate run allowance. Streaming
uses chunks of at most 1 MiB and refuses invalid budgets, leaf symlinks, exceeded
byte/time limits and file-identity changes. Bound budgets are retained for later
run-boundary and publication rechecks. Model bytes establish a digest only, not
model format, index compatibility, readiness, licensing or completed annotation.
No model or source download is performed.

Optional local-plan/import flags `--run-bindings RUN_BINDING.json --bound-file
role=/explicit/path ...` rehash every role again, compare the exact boundary inputs
and preserve source/profile identity. COMPLETE receipts must additionally match
run_id, run_bindings_sha256 and evidence_kind; all required roles must be bound.
Changed model/source/config/log/output bytes or a new run claim with an old binding
refuse before publication. The publication guard rechecks input bytes once more.

BOUND_DECLARED_FILES_ONLY is not runtime or upstream success. The model validation
field always says BYTE_DIGEST_ONLY_NOT_MODEL_READY and licensing/runtime/execution
holds remain. A run ID binds declared identity, not global uniqueness or elapsed-time
freshness. Coherent historic inputs/receipt remain historic unattested evidence;
no wall-clock assertion or authentication is invented. Generic TSV mapping still
needs its own columns/row contract; a source byte pin alone does not validate an
upstream output schema. Planning always remains HOLD / NOT_EXECUTED.
