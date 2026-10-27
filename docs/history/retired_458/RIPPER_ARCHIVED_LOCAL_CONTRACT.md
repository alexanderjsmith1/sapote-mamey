# Archived RiPPER local contract — source-backed, no upstream execution

Retired in v9.7.458 and kept as a record. Settings and commands may be out of date. Current guide: [RiPPER optional adapter](../../RIPPER_OPTIONAL_ADAPTER.md).

This review supersedes the earlier unknown-local-input/header statements. Parent
supplied archived original source at revision
`e90b3e6e74ddee99685183ca421323737012a991` (2025-01-30), snapshot
`fa25d107f4c30f11fab0379ec6270de00fde3772`. All eight supplied content files were
independently checked against recorded SHA-256, Git blob SHA-1, and the archived
root listing. Derived metadata in `tools/ripper_source_profile.json` records exact
reviewed hashes and [Software Heritage content URLs](https://archive.softwareheritage.org/api/1/revision/e90b3e6e74ddee99685183ca421323737012a991/).
No upstream source is vendored or executed by this adapter.

## Verified local input and selection

`ripper_local.pl` GetOptions accepts `-queryfn`, `-conffile`, `-outdir`, `-fofn`,
`-indir`, and positional input GenBank paths after `--` (source lines 47–61,
234–252). A nonempty file-of-filenames supplies one path per noncomment line;
`-indir` prefixes those names. Without an existing nonempty list it falls back to
positional inputs. The archived POD still discusses RODEO CSV and abbreviates
`-query`: executable parsing and call sites are the authority here.

For each GenBank input it builds a translated-CDS protein BLAST database and
runs BLASTp against the TE query FASTA at E-value `1e-3`. `tophit()` reads only
`next_result()` and `next_hit()` (304–314, 1131 onward). This is the first result
and first hit, not exhaustive RTE discovery. The `Accession` output value is the
subject CDS identifier, chosen by priority locus_tag, old_locus_tag, protein_id,
gene, then a strand/start fallback (1055–1090). It is not the query FASTA ID or
necessarily an NCBI accession. It does not prove the subject is biologically a
RiPP tailoring enzyme. Query-context IDs must be reconciled with those subject
IDs before import; the initial adapter's restricted safe-ID alphabet still applies.

Database building traverses multiple records, but locus extraction uses the first
GenBank record (343, 911, 965). Multi-record files can therefore mismatch the
selected subject. Multiple query FASTA records similarly do not receive complete
coverage. The planner requires one GenBank record, one query context and one FASTA
sequence per held plan. It performs bounded text-structure checks only, not full
GenBank semantics, translation or BLAST validation. Separate plans do not imply
safe batch integration: database unique(acc,ppser) can collide for reused subject
IDs, and basename-derived temporary/output names can collide.

The script creates an FTP client to `ftp.ncbi.nih.gov` at startup (154), although
the main local path uses supplied sequences. It therefore cannot be called a
verified offline route. Removing that connection is a proposed software adaptation,
not existing unmodified behavior. Fixed `/tmp`, configuration/database paths,
unquoted shell command strings, unchecked subprocess exits and first-hit selection
need independent runtime review before any launcher is admitted.

The local shell wrapper uses the fixed container mount `/home/mnt`, not a personal
home or a configurable environment variable. It reads `/home/mnt/gbk/*.gbk` and
`/home/mnt/faa/query.faa`, invokes the local Perl script, postprocesses and networks.
It removes existing sqlite contents and GENENET directories and does not fail fast.
It is not admitted by this planner. The archived `local.conf` lacks `blastdbdir`,
which the local Perl route uses. A supplied planning config must explicitly declare
`sqlite3fn`, `prepeptab` and `blastdbdir`; other runtime/reference paths remain held.

## Exact export contract

`mergeRidePfam.pl` lines 124–126 emits the following ordered header for both
`out.txt` and `distant.txt`:

```text
Accession Organism PPSerial FastaID Sequence SameStrand PP_TE_Distance Prodigalscore hname signif hdesc
```

The separator is TAB. In the archived local route, main and distant counters start
at numeric 1 and 9001 respectively (ripper_local.pl 491–492), increment by 1, and
supply both the FastaID suffix and insertSQL serial argument (628/640 and 657/669).
The SQLite field ppser is INTEGER (218), and the merger writes it directly with
the stored FastaID (138). No padding/format operation is used. The source-backed
profile therefore requires positive canonical ASCII decimal PPSerial (`[1-9][0-9]*`)
and exact `FastaID == Accession + '_' + PPSerial`, before classifying the channel.
Zero, leading-zero, signed, fractional, exponent and whitespace encodings do not
represent these native counter outputs and are refused. Raw strings are retained;
the adapter does not rewrite them or infer authenticity. Modified/padded external
SQLite tables are outside this archived native-output profile. Generic TSV mode
does not apply the serial invariant. The source-backed mapping is Accession→enzyme_accession,
FastaID→peptide_id, Sequence→sequence. Other fields remain raw. SameStrand is
`yes`/`no`; the merger selects one most-significant domain hit, or `none` values.
FastaID suffix matching `_9\d{3,}$` selects the distant export; those rows require
an HMM hit from collection `ripp` and are omitted if no such hit exists. Other
rows go to main output. The local script starts distant IDs at 9001. That branch
also includes candidates beyond the annotation-count limit, so the name “distant”
must not be treated as proof of a genomic-distance cutoff. Header-only output is
not proof that upstream stages completed successfully.

Local scoring is not recalculated: source applies a same-strand score reward,
length/overlap filters and near/top-score retention; the adapter preserves exported
numbers. Neither distance nor score establishes precursor identity or BGC membership.
No candidate coordinates are available in this TSV contract. All v2 query-context,
UNVERIFIED membership and execution/provenance qualifications remain in force.

## Optional adapter commands

```text
python tools/ripper_adapter.py source-profile \
  --profile archived-e90b3e6-mergeRidePfam --out /fresh/profile

python tools/ripper_adapter.py local-plan \
  --queries one_query.json --genbank single_record.gbk \
  --query-fasta single_query.faa --config reviewed_local.conf \
  --profile archived-e90b3e6-mergeRidePfam --out /fresh/local_plan
```

Profile export writes derived metadata and `columns.json`; local planning writes
`LOCAL_PLAN.json`, always HOLD / NOT_EXECUTED. Its invocation is a placeholder
source-contract template, not an executable launch plan. It stages no inputs,
opens no network connection, probes no binaries and installs nothing.

To import a source-shaped TSV, add
`--source-profile archived-e90b3e6-mergeRidePfam --channel main` (or `distant`)
to the existing import command, retaining required columns/config/log/query inputs.
The COMPLETE receipt must additionally bind `output_profile`, `output_channel`,
and `source_profile_sha256` (the bundled metadata file's exact hash, available in
profile export `sources`). Existing exact query/columns/raw/config/log hashes remain
required. Header order, canonical mapping, subject/peptide-ID relationship and
canonical positive serial/ID pairs and their lexical channel are checked. The TSV has no HMM collection-identity column:
checking a consistent distant serial/FastaID pair and nonblank, non-`none` hname does **not** independently
prove the source's `ripp`-collection requirement. `channel_validation` explicitly
records UNVERIFIED_NOT_PRESENT_IN_TSV and HOLD_HMM_COLLECTION_PROVENANCE for distant
imports. Collection provenance needs the source database/stage evidence. Blank hit
names are refused as a stricter importer admission rule; the archived writer does
not itself explicitly forbid a malformed database's blank hname. Score/distance
fields are preserved raw, not semantically validated. Operator-supplied evidence
must declare this archived
source revision; a Docker digest is not equivalent evidence. Synthetic rows may
exercise the schema but remain explicitly NOT_EXECUTED_SYNTHETIC. Bare generic
TSV import remains available with no source-profile compatibility claim.

## Dependencies, licensing and holds

Source requires Perl ≥5.14, BioPerl (SeqIO, SearchIO, Seq, SeqFeature), DBI/SQLite,
Digest::SHA, XML::Simple, LWP::Simple, Net::FTP and standard file/option modules;
local commands call makeblastdb, blastp, blastn and modified prodigal-short.
Postprocessing requires HMMER/Pfam/RiPP HMM data and additional Perl/networking
helpers; the supplied source subset does not establish their complete runtime
versions. No dependency availability or license compatibility was tested.

No license-like file appeared at the archived root and no license grant appeared
in the reviewed source headers. This leaves licensing unverified; it is not a legal
conclusion about the entire project. The paper license does not license the code.
Parent supplied Docker latest digest
`sha256:f6abc7d5ad814ce9c9471d5425788daafd93e5de80ed3974caf8abff146541f2`,
linux/amd64, 2,882,186,579 bytes, last pushed 2023. No image was downloaded. The
archived Dockerfile clones mutable master; it does not bind this 2025 revision to
that image. **Archived-source/container equivalence remains UNKNOWN.**

A live local runner still needs admitted licensing, compatible runtime/references,
a reviewed offline/temp-path/exit-handling adaptation, authentic output/completion
logs and genomic coordinate mapping. This wave advances a verified local plan and
strict export contract; it does not approve or simulate a successful upstream run.


## Optional semantic input binding (no execution admission)

Add `--semantic-validation` to local-plan for lazy Biopython parsing. The default
text-only route remains unchanged for compatibility and now explicitly records
`NOT_REQUESTED_TEXT_ONLY`. With Biopython unavailable or failing to import, the
planner emits HOLD_DEPENDENCY_UNAVAILABLE, adds an unresolved input-semantics hold
and keeps plan_status HOLD / upstream_execution NOT_EXECUTED. Missing optional
validation is not a successful input check. Existing CLI logging shows this status.
No installation, external process or upstream code is invoked.

With the flag and dependency present, malformed or ambiguous inputs refuse before
publication. The strict profile requires one DNA record and one canonical protein
FASTA query; exact record ID/full_contig context binding; nonempty CDS inventory;
unique explicit source-priority IDs (locus_tag, old_locus_tag, protein_id, gene);
and one nonempty declared translation per CDS matching extracted DNA translation.
Whitespace IDs and missing explicit IDs are refused rather than silently deriving
source fallback names. Every CDS must have exact contiguous in-range coordinates,
strand ±1, complete ATG start/terminal stop, no internal stop, codon_start1 and
translation table1 or11. ATG makes those accepted table policies agree with the
reviewed source's default-code translation for supported inputs; no general
BioPerl/Biopython equivalence is claimed. Compound, remote-reference, out-of-range, fuzzy/partial, pseudogene,
translation-exception/slippage, ambiguous-codon and unsupported-code/start/frame
cases are outside this initial profile and refused explicitly. Non-CDS annotations
are outside this CDS validator's scope; it is not complete GenBank validation.

The declared expected subject ID must bind one CDS. Multiple exact query-sequence
matches, or an exact match to another CDS contradicting the declared subject, are
refused. A query without an exact match can yield HOMOLOGY_UNASSESSED: binding a
candidate subject feature is not running BLAST or proving homology. PASS_INPUT_BINDING_ONLY
records parser version, source IDs, 0-based CDS intervals/strand, protein hashes,
query ID and selected declaration. It does not establish TE function, BLAST's
first-hit choice, extracted window, peptide membership, HMM/Prodigal readiness or
a positive RiPPER prediction. All source/runtime/license/offline holds remain.

Portable synthetic tests include the earlier de novo readiness fixture, reverse
strand, complete left/right-edge CDS, duplicate/ambiguous IDs and exact matches,
compound/partial features, translation/frame/exception failures, missing dependency
and legacy text-only behavior. Fixture data is synthetic and copied narrowly from
the earlier lane-owned readiness inputs, with origin/hash accounting retained.
