# Reviewed native discovery contract — optional candidate

This development adapter is based on Sapote–Mamey v9.7.452 and an explicitly
adapted local RiPPER source. Native discovery is implemented and opt-in. One
supervised run on a fabricated 6000-nt record and 150-aa bait completed with exit
0 and 78 raw candidates (`SUCCESS_UNBOUND`). Its source, runtime, profile, stage
outputs and terminal bindings are retained; the result is raw discovery, with no
HMM annotation, producer-backed coordinates or BGC membership claim.

The executed header-adapted source SHA256 is
`0b92227d09bb033074ec70379ef27c4767e2ab30c7e478e76e71c3abc13be0f3`;
its profile is `local05-552e784c90c646d2`. Earlier mock and stub tests remain
separate evidence. Default preflight launches nothing. For supported inspection,
execution templates and Methods wording, see [CLI and Methods](RIPPER_CLI_METHODS.md).

## Prepare an explicit local runtime before native preflight

This is an optional development adapter. Prepare dependencies separately, then
bind the actual files for review. Sapote–Mamey's core installer and RiPPER
preflight do not provision this native runtime. The retained fabricated run is
evidence for one selected source/runtime combination, not a portable installer.

1. Select an absolute Python ≥3.12 executable for the adapter. Its environment
   needs full Biopython for strict GenBank/CDS validation and `psutil` for an
   execution attempt. Its `sqlite3.Connection` must expose `deserialize`.
   `psutil` is checked when execution is selected after other holds clear; a
   nonexecuting preflight alone does not prove supervisor readiness. Install
   optional Python dependencies into the selected environment, using that
   interpreter's `-m pip` and the approved package source. Record the interpreter
   path and package versions. Installing into a different Python will not repair
   this environment. See the bundle installation guidance for offline pip
   configuration; this adapter does not fetch missing packages.
2. Select an explicit Perl executable and library roots. Prepare BioPerl plus
   DBI, DBD::SQLite, Digest::SHA, XML::Simple, LWP::Simple and JSON::PP for that
   interpreter. Bind the eleven `.pm` roles listed below, including all five
   BioPerl modules. Verify native extensions and architecture against the selected
   Perl. Put newly provisioned modules in an operator-owned runtime directory;
   modifying system Perl or a global CPAN installation is unnecessary. Existing
   system modules may be selected explicitly if compatible. The dispatcher
   replaces `@INC` with the receipt's roots; shell activation and inherited
   `PERL5LIB` do not supply missing roots to the supervised child. Bind the
   reviewed dispatcher itself. A `.pm` filename alone does not establish that its
   native dependencies load.
3. Select `makeblastdb`, `blastp` and `blastn` from a compatible BLAST+ runtime.
   Bind each executable separately and verify the selected source's database
   suffix/readback expectations and BioPerl pairwise-parser behavior. The
   prepared controlled PATH must resolve those exact bound files. Existing
   environment binaries can be used explicitly; no global PATH or package
   installation is required.
4. Prepare the reviewed Prodigal-short source and recipe as a separate private
   build, or select an already reviewed matching binary. Record source revision,
   applied recipe, build toolchain/architecture, binary hash and behavior evidence.
   The tested private build still prints `Prodigal V2.6.3`; stock Prodigal with
   that banner, or a renamed stock executable, does not establish the short-ORF
   modifications. For a fresh build, use the source owner's reviewed recipe and a
   platform-appropriate compiler/SDK. The recorded arm64 macOS SDK build is a
   provenance example, not a tested Linux/Windows build procedure.
5. Assemble a current runtime receipt from actual component evidence. Record
   tool/module versions, successful probes, hashes, module paths and explicit
   library roots; keep build and behavior receipts beside it. Review observed
   transitive dependencies separately. Version strings and review labels are
   declarations, not authenticated authorship or exhaustive loader coverage.
   Use finite executable byte/time budgets large enough for the selected files.
   Automatic observed-closure binding admits only files under the explicit Perl
   roots; probe/driver evidence outside them needs separate explicit file roles
   or independently retained before/after checks. The completed run used manual
   checks of 191 observed files, not the automatic closure flag.
   The retained run selected 64 MiB and 30 seconds per executable; its private
   Prodigal-short was 28,261,232 bytes and BLAST+ files exceeded the old 16 MiB
   default. These are measured example values, not universal requirements.
6. Select a coherent archived base, cumulative adaptation patch, adapted source,
   owner receipt, source closure and generated adapted profile. The N3 interface
   also needs `source_discovery_contract`. Keep config and input declarations
   immutable and explicitly bound. The config's `prodigalshortbin` must equal the
   bound absolute binary path. Config values cannot contain whitespace, so a
   native runtime path used there must satisfy that restriction; shell quoting
   cannot repair an incompatible config value. Choose a fresh absolute run root
   outside source/input trees with ordinary nonsymlink parents. Leave the inner
   `upstream_run` and runtime temporary directories for the adapter/source to
   create.
7. Invoke `lifecycle` with `--spec`, `--adapted-profile`, `--run-root` and repeated
   `--file ROLE=PATH` arguments for the exact roster. This default invocation
   performs preflight and writes held/review records without launching native
   programs. Review the concrete request before adding a matching
   `--native-admission` and `--execute-native`. Resuming a reserved preflight also
   requires `--resume-preflight` and the pristine directory contract. After the
   staging-publication update, preserve the canonical terminal and its validated
   staging alias; removing retained evidence to make a directory look pristine
   is not recovery. A changed dependency, source, input or policy invalidates the
   old request. Previous one-run admission cannot be reused.

The retained fabricated native run used Python 3.12.14, Biopython 1.88 and
psutil 7.2.2; `/usr/bin/perl` 5.34.1 with a private BioPerl 1.7.8 source library
and explicitly selected macOS system modules; existing workspace BLAST+ 2.17.0+;
and a private arm64 Prodigal-short build from source commit
`004218fbeb2cf54fe12d88ec2eede6a27d70ebf7`. It combined existing system/runtime
files with private artifacts; it was not a completely self-contained Perl
installation. Other platforms and fresh installations remain unverified.

Discovery does not require HMMER or Pfam/ripp model installation. HMM annotation
is a separate stage with its own executable/model/index and provenance contract.
The consumed fabricated run returned `SUCCESS_UNBOUND` with 78 raw rows and
`SCOPED_BOUND_BYTES_ONLY`; HMM annotation was not run and candidate membership
remains unverified. This historical outcome does not authorize another run or
establish biological performance, portability or distribution clearance.

## Discovery is separate from HMM annotation

The selected Perl source does not run HMMER or read Pfam/ripp models. Discovery
produces a fresh nine-column SQLite table, optional candidate FASTA, a window
GenBank export and stage receipts. Its reserved empty summary is not the final
merged HMM table and cannot establish no-hit. HMM annotation needs separate
source/resource/postprocessor admission and remains NOT_RUN. Existing merged
eleven-column import is unchanged. Raw discovery does not enter canonical scores.

## Source, runtime and input admission

Use mode=adapted_local05 and the matching adapted-source profile. Original base
+ cumulative patch must reproduce adapted source in memory. source_closure
selects the source handoff JSON and must match that triplet/revision.
Adapted bytes are never silently accepted under the original source pin.

Required native roles, each explicitly supplied as ROLE=PATH and SHA256-bound:

- archived_base, source_patch, upstream_source, adaptation_receipt, source_closure;
- config, genbank, query_fasta, queries;
- perl_runtime, makeblastdb, blastp, blastn, prodigal_short;
- runtime_receipt, prodigal_recipe, perl_dispatcher;
- the eleven perl_module_* roles defined by MODULE_ROLES.

The module names are Bio::SeqIO, Bio::SearchIO, Bio::Seq, Bio::SeqFeature::Generic,
Bio::Species, DBI, DBD::SQLite, Digest::SHA, XML::Simple, LWP::Simple and JSON::PP. A role is
perl_module_ plus the lowercase module name with :: replaced by _. Bind the
actual .pm file; its path must agree with the selected explicit Perl library roots/suffix.
Missing prerequisites produce HOLD with the exact missing roster. No search,
installation, compilation, download or native probe occurs in preflight.

runtime_receipt uses schema ripper-native-runtime/1 and state
PROBED_NATIVE_RUNTIME_CONTENT_UNATTESTED. It includes tool_sha256, tool_versions,
module_sha256, module_paths, module_versions, perl5lib, tool_probe_exit_codes,
module_probe_exit_codes and probed_interpreter_sha256. Every required probe
exit code must be integer zero; missing/unavailable declarations stay held.
Executable/module bytes must match. Required behavior decisions are:

- prodigal_short_validation=SHORT_ORF_BEHAVIOR_REVIEWED;
- blast_database_format_validation=REVIEWED_FOR_SELECTED_SOURCE;
- blast_pairwise_parser_validation=REVIEWED_FOR_SELECTED_BIOPERL;
- prodigal_recipe_sha256 matches the explicit recipe file.

These are byte-bound reviewed content declarations, not authenticated authorship
or fresh probes performed by the adapter. Parent review must inspect actual
probe evidence, native extensions/transitive dependencies, architecture and
short-ORF behavior. By default the lifecycle rechecks explicit file roles.
Selecting `bind_observed_runtime_closure` also rechecks its bounded observed
library-file roster; neither route provides exhaustive operating-system or
dynamic-library integrity monitoring. Additional reviewed files may use remaining
roles within the 32-file cap.

A nonempty immutable config is mandatory. Allowed keys are prodigalshortbin,
prepeptab, sqlite3fn, blastdbdir and seven source-supported numeric controls in
NUMERIC. Duplicate/unknown keys, leading whitespace, extra fields, symbolic
paths, invalid/range-exceeding numbers and unsafe SQL identifiers are refused.
prodigalshortbin must equal the exact bound executable path. Values cannot
contain whitespace. If supplied, SQLite/blastdb paths must equal fixed fresh
child namespaces; otherwise the source defaults apply.

Strict Biopython semantic validation is required for native admission: one
record/query, unique source-priority CDS IDs, complete exact contiguous ATG CDS
translations and tables1/11. The first native scope requires an exact unique
query/selected-CDS match. Ambiguous/unsupported inputs remain refused/held.
Actual BLAST subject selection still requires raw-output checking. Enzyme query
context is never peptide location.

## Exact argv, parent review and opt-in dispatch

The adapter constructs only this argv, without a shell:

    <Perl> <bound dispatcher> <library count> <explicit library roots...>
    <adapted source> --run-root <outer>/upstream_run
    --temp-root <outer>/upstream_run/temp --conffile <bound config>
    --outdir <outer>/upstream_run/output --outfile summary.tsv
    --queryfn <bound FASTA> -- <bound GenBank>

The child root remains absent until source launch. Controlled PATH must resolve
makeblastdb/blastp/blastn to their exact bound executables. Prodigal-short uses
the absolute configured path. Library roots come from the bound runtime receipt and replace @INC through the
explicit bound dispatcher; inherited PERL5LIB/PERL5OPT and loader overrides are
excluded. TMPDIR is the fresh outer/runtime_tmp; HOME is not repurposed.

Default lifecycle preflight writes NATIVE_REVIEW_REQUEST.json when sufficient
inputs exist. It binds spec, all explicit files, selected adapted profile,
runner/helper code hashes, semantics, argv and environment under contract
ripper-native-discovery/1. Its decision is PENDING_PARENT_REVIEW.

After reviewing the concrete request, the parent can supply --native-admission
with matching ripper-native-admission/1 content, reviewer=parent,
evidence_kind=operator_supplied, decision=APPROVED_NATIVE_LOCAL_EXECUTION and
local_use_decision=REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE.
All other request fields must match. Changes invalidate admission. Matching
content is explicitly unattested; a label is not a human signature, native
success, biological function or distribution-rights certificate.

Complete reviewed preflight is READY_NATIVE_REVIEWED_NOT_EXECUTED. Only
--execute-native enables supervised native dispatch. Missing prerequisites
or review still yield HOLD without calling the launcher. --execute-stub cannot
invoke native mode.

If preflight reserved the outer root, also select --resume-preflight. Only an
ordinary pristine directory containing PREFLIGHT.json, TERMINAL.json and
NATIVE_REVIEW_REQUEST.json can resume. Current publication also retains
TERMINAL.json.staging, which must be the validated same-file alias of the canonical
terminal. Legacy three-file preflights remain supported. Its source/files/profile/
root/request must match and its previous terminal must show no upstream execution.
Retained staging is not removed to manufacture a pristine directory. Exclusive
EXECUTION_PREFLIGHT.json and EXECUTION_TERMINAL.json preserve initial records.
Additional/stale content or a second attempt is refused. The actual source-created
upstream_run leaf remains fresh. A separately reviewed future fresh-root request
can also dispatch directly without a reserved preflight.

Both routes share the sampled wall/RSS/disk, cancel-file/KeyboardInterrupt and
process-group supervisor. Logs, outputs and process status are retained; inputs
are rehashed before/after. A successfully launched native process is recorded
as EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED even if it fails. This records launch,
not biological success. Unlaunched/held work stays NOT_EXECUTED. Missing terminal
is not completion. Limits are supervisory, not hard quotas or a network sandbox;
detached/reparented processes and broader native workloads remain outside the
completed single fabricated smoke test.

## Raw output interpretation

After supervised zero exit, the exact bounded SQLite bytes are deserialized into
an in-memory snapshot with query-only/trusted-schema-off and memory temporary
storage. A missing SQLite deserialize capability is a preflight HOLD. Live sidecars,
wrong columns, missing unique (acc,ppser) identity and over10000rows are refused.
Serial/FastaID, sequence alphabet/length, strand, finite scores and nonnegative
distance are checked. Original accession/peptide IDs remain unchanged.

Stage STARTED/terminal rosters, schema, argv/contract, zero raw status and output
hashes must agree. BLASTp hit/no-hit declarations and BLASTn/Prodigal row shapes
are checked independently. Database binary format is not certified by this
parser. Generated temporary inputs removed by the source cannot be rehashed
afterward; lineage/native-format claims depend on reviewed source/runtime evidence.

SQLite sequences must match exported FASTA exactly. Missing exports, incomplete
stage coverage or a different BLAST subject are AMBIGUOUS: candidate_count null,
raw rows/original IDs retained. No-hit requires the exact three-stage BLAST
no-hit path with no contradictory exports. A full five-stage run with zero
retained rows is NO_RETAINED_CANDIDATES. Zero exit/empty summary alone is never
no-hit. Nonzero exits, failed stages, malformed output or changed hashes are
FAILED; cancellation/resource triggers are INTERRUPTED. No outcome infers
biological absence.

RAW_DISCOVERY.json is separate from merged HMM evidence. Annotation is NOT_RUN,
membership UNVERIFIED and coordinates ABSENT_PRODUCER_MAPPING. GenBank window
coordinates and the enzyme query do not automatically locate original peptides.
Existing provenance-pair mutation controls remain mandatory. Distribution/license
and scientific holds stay visible after explicit local execution admission.

## Peer correction boundary

F4 inherited four saved-F3 lifecycle defects. F5 retains EPERM cleanup uncertainty
even after leader exit, catches final hashing/parsing interruption, classifies
inspection denial as unavailable supervision (native HOLD), and binds parsed
result bytes to the same consumed generation. All retained outputs are rechecked
before terminal publication. Counts are not admitted on failure/interruption;
primary and cleanup/finalization diagnostics remain separate. SQLite and stage
text parsing now consume captured bytes, with source hashes and final drift checks.
This does not guarantee future immutability after publication or recovery from
repeated terminal-write interruption, SIGKILL or machine loss.

## Explicit N3 source profile

F6 admits the exact N3 base/patch/postimage/owner bytes into a distinct local
review-only profile. Historical Q3 artifacts remain unchanged and reject N3.
Only explicitly registered source interface hashes (including the reviewed
header-adapted N3 source) can close the
native interface hold; an unknown adaptation remains held even if its patch is
byte-consistent. There is no automatic source/profile selection or parent adoption.

For N3, source_closure is the explicit NATIVE_SOURCE_HANDOFF.json and the extra
source_discovery_contract role binds NATIVE_DISCOVERY_CONTRACT_PROPOSED.json.
The source, archived base, cumulative patch, owner receipt and nine SQLite column
names must agree. The N3 argv puts --queryfn before --outdir and omits --outfile;
Q3 keeps its historical argv. Both phases require blastn and never require HMM
models for discovery. New adapted profiles record separate discovery and HMM
annotation metadata; this is a static interface review, not native validation.
Bio::Species now has an explicit module file/version/probe binding alongside the
other runtime modules. Consumer config remains deliberately narrower than N3's
Perl parser: no whitespace values/indentation or unlisted keys. The first native
input scope still requires exact self-match; N3's unrelated-query negative-control
design is not silently admitted as a new native input scope.

A successful N3 source normally writes fresh inner-root DISCOVERY.json. The
consumer requires its exact schema, unattested qualifiers, four explicit source/
config/query/GenBank bindings, paired terminal-stage roster, TE-match flag and
candidate count to agree with captured raw artifacts. Receipt locators are only
compared; external files are never opened from receipt-declared paths. Missing
N3 declaration makes the raw result AMBIGUOUS with null candidate_count. Changed
input bindings, malformed/promoted qualifiers, duplicate stage references or
count/state contradictions are refused. A declaration cannot replace independent
supervisor zero exit or establish native-format/biological success. Three source
states remain separate: NO_TE_HITS_DECLARED_UNATTESTED,
TE_MATCH_NO_CANDIDATE_ROWS_UNATTESTED and TE_MATCH_WITH_ROWS_UNATTESTED.

The four peer lifecycle corrections and consumed SQLite/stage snapshots from F5
remain mandatory for both source generations. Runtime, process behavior, native
format, coordinate, license/distribution and release acceptance still need review.
At the F6 profile-development checkpoint, no native source program had run. The
subsequent header-adapted N3 run is recorded at the start of this document.

## Installed executable byte admission

The earlier fixed16MiB tool guard rejected installed workspace BLAST+2.17.0
binaries (makeblastdb18,283,888B; blastp23,341,552B; blastn23,357,952B). They
were available files, not missing tools. Executable roles now support explicit
streaming byte/time policy through executable_byte_budget and
executable_hash_timeout_seconds. Earlier byte-admission controls used
32MiB/10seconds, sufficient for these exact leaves. The retained native run
selected64MiB/30seconds per executable. The maximum512MiB/300seconds remains finite. Hashing uses1MiB chunks and
checks descriptor/path identity. No installed executable is copied or run by
byte admission. The old default16MiB shape/limit remains compatible, using chunks.
Small textual inputs stay5MiB, and model policies remain independently bounded.
Native review binds the spec/policy and exact hashes; rechecks repeat that policy.

Saved05audit distinguishes system Perl5.34.1 (DBI/DBD::SQLite/XML::Simple/LWP::Simple
loaded, BioPerl missing in its probed path) from workspace Perl5.32.1 (those
noncore modules unavailable in its own path). Module availability from one runtime
is not transferred to another. Stock Prodigal2.6.3 is not Prodigal-short. Historical
17-role HOLD means unprovided profile bindings, not17absent laptop tools. Later
setup evidence was supplied for the completed fabricated run;
use its exact runtime receipt rather than treating the earlier probe as current.

## Rich-parser dependency contract

Strict semantic and coordinate validation require Biopython's full feature,
location, qualifier and translation behavior. Guarded dependency loaders raise
an explicit RuntimeError when optional Biopython is unavailable; the validation
boundary turns that refusal into HOLD_DEPENDENCY_UNAVAILABLE. No thin-parser
fallback is used for these strict requirements, and no feature/translation check
is relaxed. Installed Biopython continues through the unchanged strict checks.
This conforms to the existing guarded-rich-parser branch of the bundle's GenBank
shim lint rule; the lint source and allowlists are not modified. Missing-parser
behavior and the current contract check are included in final composition tests.

## Native dispatcher and temporary namespace

The required perl_dispatcher role binds the reviewed lane05 R2 dispatcher,
SHA256 dc242b1fdc5f031cc6b82638ad034ac12ac7dd4dd026353d57be56276848089d.
It receives the explicit library count/roots, replaces @INC and sets $0 to the
bound adapted source before loading it. Unknown dispatcher bytes stay held.
The native review binds dispatcher/file, argv and environment hashes. Python
rejects /Network library roots before filesystem checks; implicit default Perl
search paths are not retained by the dispatcher. Runtime library content and
actual dependency closure still require admission.

Preflight does not create runtime_tmp or the inner source namespace. Only an
explicitly reviewed execution creates fresh outer/runtime_tmp for TMPDIR, then
launches; upstream_run/temp/output/SQLite remain absent for source admission.
Runtime temp is distinct from the source-owned temp leaf and included in root
disk accounting. Failed attempts retain it and refuse a second pristine resume.
This is namespace control, not a filesystem/network sandbox or native success.

### Observed native Prodigal column header

The source-pinned private arm64 Prodigal build produced a single unprefixed
13-column header (`Beg`, `End`, `Std`, `Total`, `CodPot`, `StrtSc`, `Codon`,
`RBSMot`, `Spacer`, `RBSScr`, `UpsScr`, `TypeScr`, `GCCont`) before numeric
rows. The raw consumer recognizes that exact tab-separated header only as the
first nonblank, noncomment line. It permits one occurrence; changed, repeated
or misplaced headers remain invalid numeric rows. First-four-column numeric
validation and the distinction between score rows and no reported score rows
remain unchanged. Header-only output establishes no biological absence.
The real fabricated score fixture binds binary SHA256
`9466a263c52eafb236af7bde6c9a1014c0697adb7abc5fadc699af076b26eca0`
and output SHA256
`07f6cc25bf192462a2a646561630e0cb8ce5d689516f14c6f5bfad687f7c0ceb`.
Consumer compatibility does not itself admit a new source/profile or authorize
a native RiPPER launch; the source owner and parent review those separately.

### Parent-reviewed header correction and observed runtime files

Source SHA256 `0b92227d09bb033074ec70379ef27c4767e2ab30c7e478e76e71c3abc13be0f3`
uses the N3 interface after the parent-reviewed three-line exact-header correction.
The original N3 pin remains available with its original profile. Rebinding requires
a coherent new base/cumulative-patch/source/owner/contract profile; historical
profile hashes cannot approve the new source. All scientific numeric/filter logic
remains unchanged. Component capability establishes no native RiPPER outcome.

A lifecycle spec may explicitly select `bind_observed_runtime_closure: true`. That
selection binds `transitive_loaded_bindings` from the explicitly bound runtime
receipt. The roster must contain 1–512 unique regular-file bindings under the
explicit Perl library roots, at most 5 MiB per file and 64 MiB total. Network and
parent-traversal locators are refused before reads. Exact path/size/hash bindings
join the lifecycle input roster and are rechecked before launch and during final
validation. Without explicit selection, the lifecycle does not automatically
follow or recheck that optional roster. Independently recorded before/after checks
remain separate evidence, as in the completed fabricated run. Observed files do
not prove an exhaustive runtime
closure or absence of later dynamic loads. Native RSS may be capped at up to 2 GiB
for the parent-authorized bounded native route; synthetic stubs retain a 1 GiB
ceiling. Sampling remains supervisory and can overshoot; it is not an OS quota.
