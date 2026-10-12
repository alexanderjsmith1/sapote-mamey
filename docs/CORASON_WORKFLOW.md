# CORASON — optional public-input locus comparison

This external companion is off by default. `tools/corason_adapter.py` provides
`plan`, `run`, and `read`; core Mamey extraction, scores, sealed packages and the
stored-antiSMASH-only figure lane do not invoke it. Public source provenance does
not authorize publication: derived outputs are PRIVATE. A later public projection
requires its own reviewed fields, identity, provenance and disclosure scope.

The initial method profile is original nselem/corason commit
`aa70dddebafb210445794fd24b1c6b2e4177c58c` (AGPL-3.0), not myCORASON/Corason3.
Internal POD `0.01` is not a release. Source, dependencies and models remain
external; the adapter installs, downloads and vendors none of them. Current M5
availability/runtime compatibility is unverified. The inert registry marker reports this optional runtime as not probed/present;
it does not establish runtime readiness.

## Separate admission records

All JSON inputs are bounded objects. SHA256 values are exact lower-case hashes.
Caller-supplied review records are explicit operator evidence, not cryptographic
certificates or permission grants. The operator must review and affirm the bound
plan with `--approved`; documentation and receipt contents cannot authorize it.

`corason.public-intake.v1` contains a `records` list. Each source record names
`package`, `package_manifest_sha256`, `source_zip`, `source_zip_sha256`,
`source_bytes`, and file bindings for `public_receipt` and `validation_receipt`.
A file binding is `{path, bytes, sha256}`. The current producer package supplies
`strain_id`, exact full contig, typed `node_id`, `antismash_region`, `bgc_id`,
`start`, `end` and `source_gbk`; original source SHA must match that package.
Raw ZIP-only loci without a package alias binding are held. Full source identities
are case/version sensitive; no shortened-node or bare-alias repair is made.

The public receipt schema is `corason.public-source-review.v1`, state
`REVIEWED_PUBLIC_SOURCE_BINDING`, exact `source_zip_sha256`, `accession_versions`,
and `primary_sources` (HTTPS URL, accession_version, metadata_sha256). Native
admission additionally requires scope `PRIMARY_PUBLIC_SOURCE_BINDING` and NCBI/ENA
source hosts. The review must reconcile the exact original local archive/record
roster with that public provenance; a folder name or taxon match is insufficient.
Metadata accession provenance alone is not sequence-byte identity or redistribution
clearance. The package-validation receipt schema is
`corason.package-validation-review.v1`, state `VALIDATED`, scope
`ACTUAL_PACKAGE_VALIDATION`, package_tree_sha256 and exact original validation
`evidence_path`/`evidence_sha256`. This projection preserves the actual validator
receipt/log without inventing a validator schema. Original source/package/review
bindings are rechecked on run and read, including failure handoff.

`corason.selection.v1` declares an ordered unique list `loci` of full display
identities and `query={exact_locus,locus_tag,translation_sha256}`. The query digest
binds one original saved CDS translation, including a terminal stop if present.
Selection is fixed before outcomes. Every unselected source locus remains in the
original denominator. No query optimization, automatic reference retrieval, gene
prediction or new translation is performed.

`corason.runtime.v1` supplies `profile=corason-original-aa70ddde-region-v1`,
`kind=NATIVE`, an `identity` object and bound `review_receipt`. The runtime review
schema is `corason.runtime-review.v1`, `intent=NATIVE`, state `REVIEWED`, exact
canonical identity_sha256 and observer_sha256. Review records are operator evidence
projections, not self-authenticating execution or publication clearance. Identity includes:

- commit; source_root; helpers mapping each exact CORASON filename to a file
  binding; `entry` equal to the corason.pl helper binding. The native helper set
  and Git blob IDs must match all 28 pinned primary directory entries.
- interpreter and observer_python file bindings; actual host architecture;
  perl_modules_reviewed, transitive_io_reviewed; environment_receipt binding and
  explicit environment/PATH. The review covers dynamic libraries, Perl/BioPerl,
  scientific executables and transitive I/O, not merely a displayed banner. All six
  thread controls OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS,
  NUMEXPR_NUM_THREADS, VECLIB_MAXIMUM_THREADS and OMP_THREAD_LIMIT must equal
  the string `1`; PYTHONDONTWRITEBYTECODE must also equal `1`. These controls do
  not override the original BLAST explicit twelve/four-thread arguments.
- tools mapping names to exact file binding, probe argv, reported_version and
  probe_stdout_sha256/probe_stderr_sha256. Required scientific children are BLASTp,
  makeblastdb, MUSCLE, Gblocks, FastTree and nw_topology/nw_display/nw_labels.
  Other source-required children must be added to this reviewed closure.
- entry_help_stdout_sha256. Entry --help and each admitted tool probe must return
  zero and match the bound profile; unknown versions/resources do not fall through
  to an unreviewed PATH tool.
- prefilter_observer=`ReadingInputs-before-deletion-v1` and resources:
  source_reviewed, prefilter_stage_reviewed, parallel_runs=1, cpu_total,
  effective_tool_threads for all scientific tools, max_concurrent_children.

Native direct execution requires a safe external source-root layout
`source_root/CORASON/<helper>`; an unrelated entry script is not accepted even if
it prints the same version. Native profile evidence is not available merely from
writing this manifest. A separate future compatibility trial must establish it.
Synthetic tests use kind/intent `SYNTHETIC_PROTOCOL_TEST`, explicit fixture hashes
and synthetic review scopes; every result remains SYNTHETIC_PROTOCOL_ONLY and
cannot become native/public biological admission by changing a label.

## Resource and filesystem boundary

The original source uses BLASTp `-num_threads 12` for tabular query search and
`-num_threads 4` for its parser search. It has no admitted universal one-thread CLI.
Native cpu_total must cover at least twelve CPUs and the reviewed maximum child
threads/concurrency. It must also be no greater than the actual positive
`os.cpu_count()` observation at plan/run/read. Missing observations or a host
reporting ten CPUs refuse this twelve-thread profile. This is a conservative
policy ceiling, not a measurement of affinity/cgroup allocation; no oversubscription
flag or caller-rehashed JSON budget bypass is supplied. The observation is recorded.
The observer also refuses an explicit BLAST thread request
above that total. Review other tool defaults; do not invent `--threads`, force a
small resource claim, or assume a watcher enforces CPU affinity.

Execution is serial, foreground, nice15 where available, observed RSS limit
3.8GB, total timeout1800s per whole run/read worker, and minimum free disk2GB
on both receipt and native-work roots. One outer watched Python worker includes
staging, Biopython allocation, conversion, tool probes, native analysis and Python
readback. Native children and probes inherit its process group; there are no nested
watcher sessions. Direct child receipts bind argv/cwd/exit/logs and identify the
outer monitoring scope. Probes additionally have a ten-second direct-child timeout;
a timeout aborts the worker and its owned descendants. Periodic process-tree
observation is not a kernel sandbox. Exact runtime/transitive
write review or a separately implemented reviewed container profile is required.
Containers are not supported implicitly by this initial direct-entry driver.

The plan takes explicit `--write-root` (human-facing receipts/exports) and
`--native-work-root` (existing, permitted shell-safe directory). Upstream shell
strings cannot safely execute inside a space-containing path. The latter is
separately admitted, may be a permitted `/private/tmp` child, and is bound in the
plan. No directory is silently created outside that selected boundary. Source
helper/interpreter paths must also be shell safe; full display identities live
in crosswalks rather than filenames. Optional `--read-only-root` protects named
research roots; it supplements filesystem permissions and immutable input binding.

Plan/out/work/read destinations cannot overlap protected inputs, runtime source,
package or bundle. Occupied empty/nonempty directories, dangling symlinks and
racing reservations refuse. There is no resume/force path. Failed owned attempts
retain diagnostics/products; existing outputs and external inputs are not deleted.
The read handler writes a new export directory, never a package mutation.

## Commands and actual phase semantics

Prospective shapes, requiring separately admitted records and approval:

```
python tools/corason_adapter.py plan --intake <intake.json> \
  --selection <selection.json> --runtime-manifest <runtime.json> \
  --native-work-root <permitted-safe-root> --write-root <output-root> --out <fresh-plan>
python tools/corason_adapter.py run --plan <fresh-plan/PLAN.json> \
  --write-root <output-root> --out <fresh-attempt> --approved
python tools/corason_adapter.py read --run-receipt <fresh-attempt/RUN_STATE.json> \
  --write-root <output-root> --out <fresh-export>
```

`plan` reads metadata/hashes only; it does not probe executables, extract sequence
payloads or run searches. Missing/unreviewed public/runtime metadata refuses before
output creation. A valid plan records its outstanding modern-format/conversion
check, and COMMAND.sh is a refusal stub, never a runnable native shortcut.

`run` checks the bound runtime before launching an executable, reserves a fresh
controller receipt directory, then rederives selection and original source inside
the whole watched worker before any sequence staging. It reserves a fresh native
work directory. Early worker refusal preserves a failed controller receipt without
a native work directory; it does not create an admitted success proof. It stages only exact selected public region
members and their saved query translation, preserving unknown metadata. Imports
of Biopython occur only in this explicit conversion stage. Unsupported fuzzy/
compound CDS geometry, missing/duplicate tags, multiple translations and internal
stops refuse. One terminal stop may be removed with both original and converted
digests recorded; no other amino-acid transformation is performed.

The converter phase is the exact admitted interpreter plus
`CORASON/gbkIndex.pl CORASON_GENOMES CORASON`. A run-local read-only helper view
points to the external original source; it is not a vendored source copy. The
converter deletes its existing GENOMES/ID files, hence it sees only a fresh work
area. Before analysis, verify every converted gene, actual numeric org mapping,
source CDS ordinal/locus tag, strand/oriented 1-based coordinates and translation
against the independently parsed source. Check the exact fourteen-column native
schema: its locus_tag heading contains accession while sequence_accession contains
the original locus tag. Numeric IDs are read from the converter, never inferred
from ls/input order. Zero exit with a dropped/swapped gene is failure.

Analysis calls original corason.pl in --conda/explicit RAST mode with checked
reference org and full selected numeric list. It supplies source defaults
explicitly: e_value1E-15, bitscore0, cluster_radio10, e_cluster1E-3, e_core1E-3,
rescale85000. These are compatibility defaults, not optimized biological choices.
Automatic --gbk mode's grep-based reference binding is bypassed in favor of the
verified conversion checkpoint. --conda selects relative helper/output semantics;
it is not an installation claim.

Generated process-local witnesses bind actual scientific children, original
1_Context_text.pl and ReadingInputs.pl. The latter snapshots bounded actual
.input/.input2 and tabular BLAST evidence **before** the original filtering helper
deletes neighborhoods, then delegates to the exact original source. Generated
observer bytes, config, actual argv, child status, stdout-compatible execution and
source/tool hashes are recorded. No synthetic success flag replaces that capture.
Any failed/nonterminal witnessed child refuses completion even if the upstream
parent masks its exit. A future reviewed policy for intentional failed-stage
fallbacks would be a separate compatibility change; this initial profile is
conservative. Resource stops invalidate zero exit.

WORKER_REQUEST, WORKER_STATE, WHOLE_WORKER.log, WHOLE_WORKER_RECEIPT,
PRELAUNCH_MANIFEST, RUN_STATE, EVENTS and phase logs retain partial/failure
provenance; successful runs add RUN_MANIFEST and SELECTED_RESULT, followed only
after successful outer monitor closure by WHOLE_WORKER_ADMISSION. The acyclic
admission descriptor binds the terminal run state, request/method and outer
receipt; it is not inserted into its own hashed producer. A killed worker cannot
leave a consumable success receipt merely by writing a result before the stop.
Read requires this descriptor and verifies argv/cwd, two disk floors, resource
limits and log hashes, then performs its own independently watched Python readback.
A failed read may preserve its own failed diagnostic directory; it has no admitted
export descriptor. File hashes are
content bindings under a stable-input/no-concurrent-writer assumption, not signed
execution attestation or protection against an adversarial operator editing all
receipts. Source/profile/output changes invalidate readback.

## Readback and truthful completion

Read checks the selected producer, actual phase argv/cwd/logs, original source,
conversion products, generated observers and native/QA artifact closure. It
recomputes readback without launching external binaries. Exact full identities
must survive native safe tokens and numeric IDs. Multiple hit neighborhoods from
one locus stay separate through source anchor CDS and neighborhood ID.

Core rows bind original fig gene IDs plus neighborhood suffixes. Per-core source
FASTA identities/translations, trimmed partition widths, concatenated matrix and
tree/order neighborhood closure are checked. Native concatenation enumerates a
directory rather than a guaranteed numeric order: the reader verifies a **unique**
observed partition order against every tip's matrix bytes. Ambiguous or expensive
matching holds instead of inventing order. This is structural conformance, not a
benchmark of orthology, alignment or evolutionary accuracy.

| Actual route | Readback result |
|---|---|
| MULTILOCUS_CORE | More than one verified core gene, at least two neighborhoods, complete core/source/partition/matrix/tree/order/SVG closure; goal MET_STRUCTURAL_ONLY. |
| QUERY_ONLY_SHAVED | Bound query alignment/tree/order and at least two neighborhoods; goal NOT_MET. |
| QUERY_ONLY_UNSHAVED | Bound unshaved query alignment/tree/order; goal NOT_MET, retaining prior-stage evidence. |
| BLAST_ORDER | Bound neighborhoods and report's BLAST-order branch; tree NOT_ASSESSED and goal NOT_MET. |
| Incomplete/conflicting | FAILED/HOLD. SVG-only, missing/empty/malformed trees, wrong core/input membership or unresolved capture never becomes multilocus success. |

Process status COMPLETE_SCOPED_EVIDENCE means verified scoped export, not that a
multilocus goal was achieved. Route/goal/scope stay explicit. Raw native SVG remains
RAW_NATIVE_SVG_NOT_VISUALLY_ADMITTED; no polished/full-identity figure is promised
without separate visual admission. The portable handoff includes complete locus
identities and route captions; raw native files remain unchanged.

Denominators include original sources/loci, selected/unselected loci, converted
CDS, bound query-hit loci, prefilter/admitted/filtered neighborhoods and actual tree
tips. Absent output is not a no-hit. A no-query-hit state requires preserved
successful tabular-search evidence with exact converted source-gene membership.
Failed format conversion stops the attempt with original selection retained; it
does not silently exclude problematic sources and call a reduced run complete.

## Validation ceiling

The focused synthetic tests use tiny N/X placeholders, fixed independent expected
coordinate/identity/count/route values, reversed native org allocation and reversed
partition order. They exercise actual fake child processes, the before-deletion
observer, conversion/refusal, whole-worker stops/admission, host CPU refusal,
thread environment, producer-bound read and preserved old outputs.
Synthetic package-validation/public-review records are explicitly fake protocol
evidence. They are not a biological reference, actual Mamey validation, public
sequence provenance or native CORASON compatibility trial.

Only root-scheduled tests after source review may establish protocol conformance.
A later approved native trial must first admit the actual environment/resources,
converter and observer route, then keep fixed original public type-strain source
order and all failures. Existing avermitilis60/sulphureus46 region denominators do
not promise compatible core or tree outcomes. Do not select favorable queries or
tune thresholds after viewing results. CORASON is new optional homology/alignment/
tree computation, separate from the established antiSMASH-only figures.

Primary source/method: [original source](https://github.com/nselem/corason/tree/aa70dddebafb210445794fd24b1c6b2e4177c58c),
[Navarro-Muñoz et al. (2020)](https://doi.org/10.1038/s41589-019-0400-9).
No compound identity, production, activity, species assignment, novelty or physical
contig adjacency claim is supported by this adapter.

The optional registry's inert NOT_PROBED marker exits nonzero without stdout/stderr,
because the existing general detector treats any printed text as presence. It
never probes the external CORASON entry and cannot report an installed/admitted
runtime from an explanatory marker. Manual runtime admission remains separate.

Human TSV exports use the existing SafeDictWriter formula guard. Canonical JSON
retains original full identity spelling. A formula-leading TSV cell gains the
existing leading apostrophe; machine joins should use EVIDENCE.json or validate
that the cell equals csv_safe_cell of its bound JSON value. Do not blindly strip
apostrophes from native identities. No native source table is modified.
