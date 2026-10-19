# Owned e90 merge proposal

This standalone proposal executes the grounded SQLite selection and writes
out.txt/out.faa/distant.txt/distant.faa plus a row trace and result receipt.
It does not launch HMMER, read models, certify annotation provenance or admit
canonical BGC/biological conclusions. No upstream source is distributed here.

Engineering target: e90b3e6e74ddee99685183ca421323737012a991.
The inspected original mergeRidePfam.pl is 5,812 bytes, SHA-256
53a2418b860d413fc1e7b7b3170026e6f637b5092fe0d2b4712fd0c11969f051.
Its writer is at lines124–174; pfs selection is at lines197–236.
The archived content identity is sha1_git:ca373fe98e7bf9a39c3652aa1f6bd91053b55aaf.

Main candidates select the first hit under SQLite ORDER BY signif across both
collections; absent hits produce three literal none cells. Distant IDs match
_9 followed by at least three digits at the end. They select only collection
ripp, and appear in distant outputs only when that query has a qualifying row.
The source's eleven headers and RiPP| prefix are retained. Sorting follows the
supplied SQLite column affinity; the unread upstream annotation schema is not
assumed numeric. This merge does not apply a new HMM significance cutoff.

The query predicate explicitly uses SQLite BINARY comparison and checks every
eligible row's exact qname. A qname column declared NOCASE remains supported,
but cannot lend one case-distinct query's hit to another query. This is an
explicit identity guard beyond the source SQL, whose schema remains unread.

Ambiguity uses SQLite dense_rank() OVER (ORDER BY signif), evaluated on the
same filtered query/collection cohort and column expression as selection.
Its peer groups honor the actual affinity and collation, including NOCASE and
RTRIM. Default TEXT retains lexicographic ordering; REAL retains numeric
ordering. No global numeric sort is introduced. This route requires SQLite
window-function support; the actual tested runtime versions are recorded in
the validation receipt. The internal rank is not an annotation evidence field.

Deliberate departures: ambiguous best-hit ties hold; duplicate raw IDs, unknown
collections, missing/failed coverage, contradictory no-hit rows and changed
file bindings refuse. Coverage is operator-declared/unattested or fabricated
software control. It cannot attest actual annotation execution. Numeric and
FASTA serialization are owned; semantic mapping is the current compatibility
claim, not byte-for-byte equivalence to BioPerl output.

Inputs: a bounded immutable ordinary SQLite file containing the nine-column
raw table and an annotation table with qname,hname,signif,hdesc,collection; a
bound coverage JSON with one state per raw ID and pfam/ripp collection; and an
explicit spec naming both tables and input SHA-256 values. SQLite sidecars are
refused. Complete empty input is distinct from missing coverage. Noncomplete
coverage never becomes a zero candidate result.

Outputs use a new directory. All streams close before publication, with
MERGE_RESULT.json linked last. Staging files and interrupted attempts remain
available. An absent canonical result is not a successful merge. Input files
are rechecked and never changed. Parent-ancestor races, hostile SQLite and a
complete runtime sandbox are outside this bounded proposal; later integration
must reuse the project's admitted filesystem/runtime boundary.

The annotation/EGN helper bodies remain unavailable from the attempted primary
views. The owned hmmscan3 tblout parser therefore remains a distinct declared
report parser, with source-compatible annotation equivalence unproven. This
proposal adds only stage S05 of the ten-stage plan. It leaves retrieval,
runtime/model admission, discovery, actual annotation, GenBank provenance,
networking, attributes/collection and core/batch orchestration explicit.

The tests use only fabricated SQLite rows and small output streams. They run
the owned SQL merge and publication path, not upstream Perl, HMMER, models,
native discovery or biology. They establish software behavior within that scope.

CLI stdout is a machine-readable receipt protocol: one eagerly encoded JSON
object followed by one newline. It uses ordinary json.dumps plus a direct
sys.stdout.write, matching established repository operators. This preserves
JSON defaults/escaping, refusal payloads, exit0/2, and encoder-before-output
behavior. Stream failures propagate as before. It is structured serialization,
not a generic terminal emitter, print alias or proxy. No health scanner, scope,
exclusion, signed waiver or emission ceiling is changed.
