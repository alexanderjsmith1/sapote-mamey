> **Historical page.** Replaced by [the native discovery contract](../RIPPER_NATIVE_DISCOVERY.md). It keeps the development record for the native RiPPER adapter: peer corrections, the N3 source profile, executable byte admission and the dispatcher binding.

# RiPPER native adapter: development record

The labels F3 to F6, N3, Q3 and lane05 R2 are internal development labels (review stages, two source-profile generations and a dispatcher revision). This page does not define them, and their source records are not bundled.

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
subsequent header-adapted N3 run is not recorded in this document. The opening section above is a peer-correction summary, not a run record. This page links no run record or runtime receipt, so the run's details are unverified here. The native-format, process and release holds above still stand.

## Installed executable byte admission

The earlier fixed 16 MiB tool guard rejected installed workspace BLAST+ 2.17.0
binaries (makeblastdb 18,283,888 B; blastp 23,341,552 B; blastn 23,357,952 B). They
were available files, not missing tools. Executable roles now support explicit
streaming byte/time policy through executable_byte_budget and
executable_hash_timeout_seconds. Earlier byte-admission controls used
32 MiB/10 seconds, sufficient for these exact leaves. The retained native run
selected 64 MiB/30 seconds per executable. The maximum 512 MiB/300 seconds remains finite. Hashing uses 1 MiB chunks and
checks descriptor/path identity. No installed executable is copied or run by
byte admission. The old default 16 MiB shape/limit remains compatible, using chunks.
Small textual inputs stay 5 MiB, and model policies remain independently bounded.
Native review binds the spec/policy and exact hashes; rechecks repeat that policy.

Saved 05 audit distinguishes system Perl 5.34.1 (DBI/DBD::SQLite/XML::Simple/LWP::Simple
loaded, BioPerl missing in its probed path) from workspace Perl 5.32.1 (those
noncore modules unavailable in its own path). Module availability from one runtime
is not transferred to another. Stock Prodigal 2.6.3 is not Prodigal-short. Historical
17-role HOLD means unprovided profile bindings, not 17 absent laptop tools. Later
setup evidence was reportedly supplied for a completed fabricated run. This page gives no locator or hash for that run or its runtime receipt, so the run is unverified here. Do not treat the earlier probe as current.

## Native dispatcher binding

The required perl_dispatcher role binds the reviewed lane05 R2 dispatcher,
SHA256 dc242b1fdc5f031cc6b82638ad034ac12ac7dd4dd026353d57be56276848089d.
It receives the explicit library count/roots, replaces @INC and sets $0 to the
bound adapted source before loading it. Unknown dispatcher bytes stay held.
The native review binds dispatcher/file, argv and environment hashes. Python
rejects /Network library roots before filesystem checks; implicit default Perl
search paths are not retained by the dispatcher. Runtime library content and
actual dependency closure still require admission.
