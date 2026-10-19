# Native raw evidence and declared coordinate evidence

Native raw results use the separate `native-coordinates` command and
`ripper-native-coordinate-reconstruction/1` packet. It evaluates the original
native qualifications directly; no conversion into `ripper-evidence/2` or
operator/synthetic execution is required. The 18 explicit bound artifacts include
the original GenBank, window, SQLite, candidate FASTA, score output, stage pair,
source/profile/configuration/query context and native lifecycle records. See
[CLI and Methods examples](RIPPER_CLI_METHODS.md#evaluate-native-coordinate-reconstruction).

The completed fabricated 78-row packet has consistent reconstructed intervals.
`NATIVE_COORDINATE_BINDING.json` records
`RECONSTRUCTED_SEQUENCE_COORDINATES_UNATTESTED`, retained-artifact origin,
recorded native execution, no instrumented producer sidecar and unverified BGC
membership. Table-1 peptide translation stays distinct from table-11 CDS/scoring
metadata; V/L-to-M correction never shifts nucleotides, and nontriplet intervals
are refused. Original raw coordinate provenance remains unchanged.

The legacy `bind-coordinates` declaration contract below remains supported for
its own imported-evidence schema. Its raw-schema refusal prevents accidental
merged-evidence relabelling; use `native-coordinates` for native raw results.

---

# RiPPER declared coordinate binding — optional, no upstream run

`bind-coordinates` evaluates one admitted evidence file, one local-plan, explicit
GenBank/query FASTA and a `ripper-coordinate-map/1` sidecar. It writes a fresh
`RIPPER_COORDINATE_BINDING.json`; it never rewrites imported evidence or canonical
packages. Current upstream scripts do not emit this sidecar. It is an interface
proposal for a separately reviewed producer or operator declaration, not a claimed
live RiPPER output. Lane05 owns upstream adaptation; this adapter consumes declarations.

```text
python tools/ripper_adapter.py bind-coordinates --evidence evidence.json \
  --local-plan LOCAL_PLAN.json --genbank input.gbk --query-fasta query.faa \
  --mapping coordinate-map.json --out /fresh/coordinate_binding
```

The structural schema is `schemas/ripper-coordinate-map.schema.json`. Envelope
hashes bind exact evidence, plan, source GenBank and query FASTA bytes. Explicit
GenBank/query paths must also match the selected plan's source bindings; changing
an input requires a new plan and map. Mapping origin is synthetic_fixture or
operator_supplied, always an unattested declaration. Missing mapping files refuse;
a valid sidecar with an empty mappings array records absent mappings, not no biology.

`subject_cds_sha256` uses SHA-256 over compact sorted-key JSON (UTF-8), as implemented
by `subject_digest`: source_genbank_sha256, record_id and subject_cds containing
subject_cds_id, source_id_qualifier, start_0based, end_exclusive, strand and
translation_sha256. Biopython semantic input binding recomputes the selected CDS.
The query FASTA ID remains separate from the source subject CDS ID.

Each mapping retains the exact upstream strings enzyme_accession, PPSerial and
FastaID; positive canonical serial/FastaID equality must match an imported row.
`sequence_sha256` binds that candidate's AA sequence. Window start/end and local
candidate start/end are positive 1-based inclusive integers, strand±1. Boolean
coordinates, out-of-bounds geometry, duplicate locations and unbound IDs refuse.
`window_sequence_sha256` is SHA-256 of the parsed window's uppercase ASCII DNA;
its representation is distinct from the raw GenBank byte digest. Original start0
= window_start1+local_start1−2, original end-exclusive = window_start1+local_end1−1.

For sequence checking, extract those original coordinates, reverse-complement on
strand−1, translate with source default code1, remove a terminal stop if present
and apply the source's initial V/L→M rule. Record transformations explicitly.
Invalid/ambiguous coding bases or unmatched translation do not become direct matches.
This check does not infer a gene, cleavage site, TE function or biological product.

Each candidate is DIRECT_SEQUENCE_MATCH_UNATTESTED, AMBIGUOUS_DECLARED_MAPPINGS,
ABSENT_MAPPING or SEQUENCE_MISMATCH. Multiple declarations remain ambiguous even
when their sequences match; the adapter does not select a convenient location.
No Biopython yields HOLD_DEPENDENCY_UNAVAILABLE. Every result retains UNVERIFIED
candidate membership, HOLD_BGC_MEMBERSHIP_NOT_ESTABLISHED and unattested execution
provenance. No region/BGC attribution follows from the enzyme's query context.

A direct sequence match proves consistency among supplied bytes and declarations,
not that RiPPER produced the map, that a window was actually analyzed, or that the
candidate belongs to the declared BGC. Authentic coordinate-export/stage receipts,
assembly/region binding and HMM collection provenance remain separate holds.


## Exact provenance qualification pairs

The parent evidence must pair synthetic_fixture with NOT_EXECUTED_SYNTHETIC, or
operator_supplied with OPERATOR_DECLARED_UNATTESTED. Independently valid but crossed
values refuse before mapping, even when every file hash has been coherently rebound.
If either per-candidate qualification field is present, both must be present and
match the exact parent pair. Legacy candidate rows with neither field remain
parent-qualified declarations; they are not silently treated as independently
attested. Coordinate assessments expose the validated parent pair explicitly.
Neither allowed pair establishes an upstream run, homology, HMM/Prodigal positive
or candidate membership. Window hashes prove supplied DNA consistency only; even
an enzyme-excluding declared window is not certified as the actual subject-centered
window processed upstream. Producer/window-execution and BGC holds remain.

## Raw and normalized identity consistency

A rebound evidence/map digest binds edited bytes, not their semantic agreement.
Before geometry evaluation, declared raw Accession, FastaID and Sequence must
exactly equal normalized enzyme_accession, peptide_id and sequence. If any of
these raw fields is present, all three are required. Declaring the archived profile
also requires all three. Contradictions or partial removal refuse; values are not
silently stripped, renamed or case-normalized. PPSerial keeps its canonical
positive-ASCII and exact FastaID rule.

Minimal legacy hand-authored declarations with none of these three mirrors remain
explicitly NOT_DECLARED_LEGACY_MINIMAL_INPUT. Matching mirrors are recorded as
MATCHED_DECLARED_RAW_IDENTITY_SEQUENCE, never authenticated native provenance.
Multiple genuine IDs/serials with identical peptide sequences remain distinct;
no sequence-level deduplication or scientific threshold/ranking change occurs.
Original source fields and identifiers are preserved. Existing mapping-execution,
HMM-collection and BGC-membership holds remain in force.
