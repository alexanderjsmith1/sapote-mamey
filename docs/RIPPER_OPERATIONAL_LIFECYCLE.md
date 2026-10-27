# Optional RiPPER byte admission and bounded lifecycle

This candidate extends the optional adapter. Default preflight launches nothing.
A fully supplied, explicitly parent-reviewed native discovery profile can execute
only with --execute-native. See [native discovery](RIPPER_NATIVE_DISCOVERY.md)
for its exact contract. Earlier lifecycle-only tests launched no native RiPPER; the later recorded fabricated native attempt is described in that guide. Its scoped result is separate from those earlier software tests.
The archive profile remains pinned to original revision
`e90b3e6e74ddee99685183ca421323737012a991`. Lane05's local adaptation is a
separate **review-only** source profile, not original upstream bytes or a release.
No install, discovery, model download, biological success or license acceptance
is implied. Candidate BGC membership remains `UNVERIFIED`.

## Select an adaptation explicitly

`adapted-profile --owner-receipt FILE --base-source FILE --source-patch FILE
--adapted-source FILE --out FRESH_DIRECTORY` hashes four explicit inputs. The
base must match the archive pin. A strict in-memory single-file unified patch
must reproduce the supplied adapted source exactly, and the owner's saved
receipt must name those patch/postimage hashes. The source must declare the
explicit run/temp-root interface. These are byte/interface checks only; no Perl
is imported or executed. Owner receipt content is bound, not authenticated.

`ADAPTED_SOURCE_PROFILE.json` records separate base, patch, adapted source and
owner-receipt hashes. To use it with `bind-run`, `local-plan` or `import`, select
`--adapted-profile FILE` and explicitly supply the four roles `archived_base`,
`source_patch`, `upstream_source`, `adaptation_receipt` with the run's other file
roles. The run binding records the exact adapted profile hash. Every boundary
rechecks the supplied files and patch relation. An operator-supplied adaptation
without that selection fails the original upstream source pin. Changing or
omitting the explicit selected profile also fails. The output TSV contract still
uses the archived headers; compatibility of a native adapted run is unverified.

## Hash large models without copying them

A run-binding manifest or lifecycle spec may select `model_byte_budget` (positive
integer, maximum 16 GiB per file) and `hash_timeout_seconds` (positive finite
number, maximum 600 seconds per file; default 30). Only these explicit file roles
use streaming: `pfam_model`, `ripp_model`, and `pfam_index_h3f/h3i/h3m/h3p` or
`ripp_index_h3f/h3i/h3m/h3p`. Each name after the slash denotes a separate suffix,
for example `pfam_index_h3f`. Hashing uses 1 MiB chunks, checks file metadata,
and repeats before publication and at subsequent admission boundaries. The
budget is per file, not a whole-roster quota. The roster is capped at 32 files.
No files are copied and no model-format/index-readiness claim follows.

Configuration, queries, context, source, receipts and output parsing retain the
5 MiB limit. The separately named executable roles python_runtime, perl_runtime,
makeblastdb, blastp, blastn, prodigal_short and hmmsearch use streamed hashes in
1 MiB chunks. Explicit executable_byte_budget (positive integer, maximum512MiB)
and executable_hash_timeout_seconds (positive finite, maximum300seconds; default30)
select the executable policy in a manifest or lifecycle spec. Budgets are per file.
For existing BLAST+2.17.0 leaves,32MiB/10seconds per file accommodates the observed
18.3–23.4MB bodies without copying or executing them. It does not establish native
format compatibility, module availability or source execution admission.

Omitting the executable byte budget keeps the historical16MiB/30second limit and
receipt shape, now hashed in chunks instead of a full bounded-memory read.
Changing executable timeout without an explicit byte budget refuses. Executable
and model policies are independent; neither expands config/query limits or borrows
the other's budget. Fresh admission/publication rehashes the selected policy.
File-descriptor and final-path identity checks refuse read-time replacement or
changes; symlink leaves are refused. No automatic tool discovery or download occurs.

## Lifecycle spec and invocation

`lifecycle --spec FILE --file ROLE=PATH ... --run-root ABSOLUTE_FRESH_PATH`
performs preflight and writes `PREFLIGHT.json` and `TERMINAL.json`. It launches
nothing by default. The spec is `ripper-lifecycle-spec/1` with `mode`, the
archived `profile_id` and `source_revision`, `files` mapping exact role to
SHA256, and `limits` containing all four fields:

- `wall_seconds`: positive finite, at most 3600;
- `rss_bytes`: positive integer, at most 1 GiB for synthetic stubs or 2 GiB for the separately admitted `adapted_local05` native route;
- `disk_bytes`: positive integer, at most 256 MiB;
- `poll_seconds`: finite, 0.01 through 0.25.

For mode=adapted_local05, select the distinct --adapted-profile and lane05
source_closure. Native discovery requires exact Perl/BLAST/short-Prodigal,
module/runtime/recipe and semantic input evidence; it does not require HMM models.
Missing actual prerequisites or parent review produce HOLD. Exact argv, executable
opt-in, review binding and reserved-preflight resume are documented in
[native discovery](RIPPER_NATIVE_DISCOVERY.md). Raw SQLite/FASTA discovery remains
separate from the final HMM-enriched table.

For `mode=synthetic_stub`, the required roles are `python_runtime`, `stub_script`
and `config`. **Only** the explicit `--execute-stub` flag launches the selected
script through the bound Python executable with `-I -S -B` and one argument,
`<run-root>/result.tsv`. This is for self-authored tiny synthetic validation;
caller-supplied scripts are executable code and their synthetic label is a
declaration, not a safety sandbox or proof of authorship. Optional psutil is
required before either native or stub launch; missing it produces `UNAVAILABLE`, without installation.

The supervisor writes STARTED, then LAUNCHED with PID/process group, stdout and
stderr logs, and TERMINAL. It monitors wall time, sampled process-tree RSS and
fresh-root disk use. `--cancel-file ABSOLUTE_PATH` checks existence only, before
launch and at each sample; it never creates that file. Keyboard interruption,
cancellation or a resource trigger stops the process group with SIGKILL and
reaps the direct child. A supervision denial is retained as `UNAVAILABLE` with
cleanup errors; it is not a successful cancellation claim. Limits can overshoot
between polls and do not enforce OS quotas or restrict network/filesystem
access. Detached/reparented descendants and native fork behavior remain
uncertified; native workflow/process behavior still requires real validation. SIGKILL of the supervisor or machine loss
can leave STARTED/LAUNCHED without TERMINAL. Those are not completion.

Final receipts bind explicit input/model/tool bytes, supervisor version, logs
and regular output files under the fresh root. They rehash inputs after a stub
run. Existing run roots are refused, and artifacts are retained on failures.
Missing/empty/malformed outputs or nonzero exits are `FAILED`; cancellation and
resource limits are `INTERRUPTED`. A strict 11-column header-only synthetic
output is `NO_HIT` **only within the self-authored stub scope**. Retained stub
rows are `SUCCESS_UNBOUND`. Both retain `upstream_execution=NOT_EXECUTED`,
`biological_absence_inferred=false` and membership `UNVERIFIED`. CLI execution failure/unavailability/HOLD returns 2 and interruption returns 130.
Preflight itself returns 0 with its explicit held/unavailable status. None of these
receipts is automatically an importable real RiPPER completion declaration.

## Validation scope

Tests use only self-authored tiny scripts and synthetic byte fixtures. Archive
and lane05 inputs are opt-in explicit read-only inputs for patch/hash checks.
Native process signalling/inspection permissions are required for supervisor
controls; sandbox denials are not passes. No original or adapted Perl, BLAST,
Prodigal, HMMER or biological upstream workflow is executed by these tests.

## Finalization integrity

Catchable final hashing/parsing interruption records an interrupted terminal when
the filesystem permits. Permission denial in process inspection or group cleanup
stays unavailable supervision; an exited leader alone does not prove its group
is gone. Cleanup uncertainty prevents no-hit/row admission. Parsed stub bytes must
match their captured digest, and retained output digests are rechecked before the
terminal. Native SQLite is queried from the consumed in-memory snapshot. Primary
errors and secondary cleanup/finalization failures remain separately recorded.
Repeated interruption while writing the terminal, SIGKILL and machine loss remain
outside this guarantee. Output hashes describe the admitted snapshot/boundary,
not immutable storage for all future time.

### Terminal publication and interruption

Terminal JSON is serialized and closed in an exclusive `<terminal>.staging` file
before the canonical `TERMINAL.json` or `EXECUTION_TERMINAL.json` is published
through an exclusive hard link. Staging files are retained and never constitute
completion. Publication is the final filesystem operation; no cleanup error can
follow it and masquerade as a failed serialization with canonical success bytes.
The receipt records this protocol and canonical filename.

A first catchable `KeyboardInterrupt` during serialization withdraws row/candidate
count admission and writes `INTERRUPTED` through a separate recovery staging file.
Original partial bytes are retained in place and hash-bound. An I/O failure during
write/close/preservation or publication, or a repeated interruption, can prevent
publication; no canonical terminal means no completed result. Prior primary,
cleanup and immediately preceding write reasons remain separate. A successful
preflight retains its staging alias; pristine native resume validates that alias
against the canonical terminal without removing either. Existing evidence is never
overwritten. SIGKILL/machine loss and errors with ambiguous OS outcomes cannot be
made transactional by this supervisor; retain all evidence and inspect publication.

### Observed process absence and RSS contributions

Cleanup records whether a process-group signal was sent, the group was already
absent at that check, or signaling was unavailable. Leader kill/reap outcomes are
recorded separately. Observed group absence does not create cleanup uncertainty;
permission denial or failed reaping retains the existing unavailable/HOLD behavior.
These observations do not certify detached processes outside the selected group.

RSS sampling explicitly assigns zero only to a member or tree reported vanished
or zombie at that sample, with bounded aggregate counters in
`rss_sampling_observations`. The counters distinguish vanished members, zombie
members and absent/zombie trees. Inspection denial is not treated as a zero
contribution; it remains `SUPERVISION_UNAVAILABLE`, with output counts unadmitted.
Polling and process-tree membership can change between samples; these observations
do not alter the existing sampled-enforcement or scientific scope.
