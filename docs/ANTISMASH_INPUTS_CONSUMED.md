# What Mamey reads from an antiSMASH ZIP

This page lists which files in an antiSMASH result ZIP Mamey reads, what each one is used for, and
where a partial ZIP leaves gaps. The short version: download the **full results archive** from the
antiSMASH web server, not only the region GenBank files, and keep the default `--json-evidence bounded`.

```bash
python mamey_run.py inspect path/to/antismash_result.zip
```

<a id="scope-identity-and-partial-reads"></a>
## Files Mamey reads

Mamey reads only regular files in the ZIP. It skips Finder metadata (`__MACOSX/`, `._*` files and
`.DS_Store`) and ignores symlinks, devices, FIFOs and sockets, even when their names end in `.gbk` or
`.json`. Extraction helpers refuse those special members before writing anything.

| File in the ZIP | What Mamey uses it for |
|---|---|
| Region GenBank, `*.regionNNN.gbk` (also `.gbff`, `.gb`) | The primary source. Each parsed region becomes a BGC record after duplicate screening, so the file count can differ from the record count. Mamey reads per-CDS `/gene_functions`, `sec_met_domain` hits with E-values, `aSDomain`, smCOG, product labels and coordinates. Parsed records feed the source scans; availability still depends on the selected inputs and configuration. |
| Whole-record (genome) GenBank | antiSMASH version, original region bounds and contig lengths (for edge and fragment flags). Used as the fallback record source when no region records parse. |
| FASTA (`.fasta`, `.fa`, `.fna`, `.ffn`) | Assembly metrics only: contig count, N50, total length and contig lengths. Not scanned for BGCs. |
| Record JSON (the large `*.json`) | KnownClusterBlast, `region_to_region`, RiQ scores and TIGRFAM (`antismash.detection.tigrfam`). Separate record readers also collect module predictions, RiPP motif cores and RRE-Finder rows. |
| ClusterBlast and KnownClusterBlast text (`knownclusterblast/*.txt`, `clusterblast/*.txt`) | Reference and ranked-organism hits. Parsed first in every JSON mode; JSON can add to it. |
| `.log` | A version cross-check and the antiSMASH record-cap check (see below). |

Main GenBank intake prefers region records and falls back to whole records. A region-only ZIP with no
true contig lengths gets unknown boundary status rather than invented genome geometry. A filename
count is not a count of parsed CDS or BGCs. Never join two records by a bare BGC alias; cite a BGC as
`strain / full node-or-contig / region / BGC alias`.

## `--json-evidence` modes

| Mode | What it does |
|---|---|
| `bounded` (default for `run`) | Streams the main JSON walker with ijson for KnownClusterBlast and RiQ under byte and leaf caps. TIGRFAM uses its own record pass. This main walker does not load the whole file. Missing ijson is recorded in `json_skipped` and makes this walker fall back to `off`; a budget overrun logs a `[WARN]` and retries in `off`. Separate record readers can still open JSON. |
| `off` | Skips the main JSON walker. KnownClusterBlast then comes from the text files. Other readers (version, strictness, original bounds, TIGRFAM) can still read the JSON, so check `tigrfam_requested` and `record_extraction` rather than assuming TIGRFAM is absent. `--capped-session` forces this mode. |
| `full` | Legacy. Loads the whole JSON and refuses files over 80,000,000 bytes (`FULL_MAX_JSON_BYTES`). Use only for small files. |

`BOUNDED_MAX_RECORDS_STREAMING` is an auxiliary-leaf retention cap of 200,000, not a count of records and not a point where the whole record walk stops. The walk continues for RiQ scores and record identity after that store fills. The main walker skips JSON members whose declared uncompressed size exceeds 250,000,000 bytes (`BOUNDED_MAX_JSON_BYTES_STREAMING`). Separate record readers have their own rules: `_iter_records` can load a whole small JSON, or use a full-load fallback when streaming is unavailable or disabled. These are not whole-run RAM limits.

The bounded time budget is 300 seconds by default. Set it with `MAMEY_BOUNDED_BUDGET_S`; `0` turns it
off. The budget covers the separate record passes too. When it runs out, the CLI retries in `off`,
and that retry can still read TIGRFAM. On a system without `SIGALRM` the budget cannot run and is
recorded as `RETURNED_GUARD_UNAVAILABLE`. This is not a timeout for the whole run.

A truncated or refused read is a gap in what was read, not evidence that a cluster or hit is absent.
Read the per-channel availability and truncation fields before calling evidence complete.

<a id="partial-input-and-bounded-reader-gaps"></a>
## When the ZIP has no record JSON

A web export of only the region GenBank files has no record JSON. Under `bounded`, Mamey then has
nothing to stream: KnownClusterBlast comes from the text files only, and there is no TIGRFAM. Intake
warns when a `bounded` or `full` run meets a ZIP with no record JSON.

Use `off` only for a capped session or for a strain whose JSON is known to break the reader.

<a id="bounded-riq-record-identity"></a>
## RiQ scores and record identity

A RiQ score is tied to the full `records[]` `id` and region number only after that record closes. Field
order does not matter. A record with a missing, blank or non-string `id`, or repeated `id` fields within that record, does not borrow
another record's identity. Scores outside a record, or in a record cut short by a parse error, stay
unassigned in `loose_hits`. The leaf cap does not stop the record walk; separate RiQ caps can hold
counts or drop member mapping.

Unassigned scores keep a per-region maximum, `riq_observation_count` and a `riq_identity_status` that
says why they are unassigned. They are left out of the genome RiQ summary and per-locus scores. RiQ is
similarity evidence, never proof of a product or activity.

## Saved RiPP motif evidence

To review RiPP motifs, ask to **read saved RiPP motif evidence** and supply the package, its source ZIP
and hash, and the full BGC identity. This reads what antiSMASH already saved; it does not run a new
predictor.

- The extractor reads every `antismash.modules.<family>` entry whose `motifs` field is a nonempty
  dictionary. It keeps motifs with a `core` or `core_sequence`, plus family, record ID, locus tag,
  motif index, leader, tail and the raw details. There is no fixed family list. Entries without a core
  are skipped.
- Rows are written to `<strain>_3_antismash_ripp_motifs.csv`, `<strain>_3_antismash_structured.json`
  and the workbook sheet `antiSMASH_RiPP_Motifs`. Check `mapping_status`, `mapping_method`,
  `source_file`, `locus_tag`, `core_sequence` and `detail_json`.
- Coordinates come from the JSON, the motif location or the matching CDS. Missing or overlapping
  geometry stays unmapped or ambiguous.
- These extra record reads run when the requested JSON mode is not `off`, or when the caller asks for
  structured evidence.
- A saved core is not a checked amino-acid sequence, cleavage site, mature product or function.
- Structured `PASS` means at least one structured table has rows; it does not mean the RiPP table has
  rows. `NULL_NO_STRUCTURED_ANTISMASH_EVIDENCE` or an error state is a gap, not a biological no-call.

<a id="antismash-record-cap-coverage"></a>
## antiSMASH record-cap check

antiSMASH can be told to analyze only the largest N records. Mamey reads the ZIP's `.log` files for
the message `Only analysing the first N records` (either capitalization). When it finds one, the run
adds `RECORD_LIMIT_TRUNCATION` to its issues: the regions cover only the analyzed records, while FASTA
or whole-record statistics may cover the full input.

The probe reports `analysed`, `first_skipped`, `skipped_count`, `probe_state` and `logs_read`.
`skipped_count` counts matching skip lines, so repeated lines inflate it. A cap header with no skip
lines still counts as truncation.

| `probe_state` | Meaning |
|---|---|
| `TRUNCATION_OBSERVED` | A cap message was found. |
| `NOT_DETECTED` | An antiSMASH log was read and had no cap message. This is a text match, not a record census. |
| `UNAVAILABLE`, `UNRECOGNISED_LOG`, `FAILED` | No log, a log that is not antiSMASH's, or an unreadable log. The CLI reports `RECORD_LIMIT_COVERAGE_UNVERIFIED`. |

If the probe itself raises an error, the CLI reports `RECORD_LIMIT_PROBE_FAILED` and writes an ERROR row
to `run_phase_receipts.jsonl`. Failures handled inside the probe use the unverified route instead, so a
missing ERROR row does not mean coverage was checked.

The truncation warning describes full-FASTA statistics, but assembly metrics can come from a GenBank
fallback or be missing. Check which source the metrics came from before quoting it. See
[assembly input scope](reference/06_CURRENT_SOURCE_SCOPE.md#volume-ii-b4-assembly-input-scope-independent-tier-fields-and-warning-limits).
Changing the JSON mode cannot recover regions antiSMASH never analyzed. That needs a new antiSMASH run.

<a id="carry-coverage-warnings-into-summaries"></a>
## Carry warnings into summaries

The full warnings live in `manifest.json` issues, `commit_receipt.json` issues and `issue_log.md`. The
compact manifest, per-strain workbook and brief are narrower and may not repeat every record-cap or
probe-failure warning. Read the full issue lists before comparing strains or quoting a genome-wide
count. The issue strings do not serialize the complete probe dictionary or an explicit source-record roster. A quiet summary cannot supply that missing source binding.

<a id="historical-external-tool-inventory-not-current-environment-validation"></a>
## Recording the antiSMASH version

Read each strain's own `manifest.json` and archive/version/hash before citing a version in Methods. Strictness is covered in [antiSMASH strictness](ANTISMASH_PROFILE.md). The following is retained historical project inventory, not validation of a current environment or cohort. A development build is not a released version.

Mamey is stage 3 of a longer pipeline. Upstream and downstream tools (with the versions
of record) are catalogued in the project's tool inventory; the essentials:

| Stage | Tool | Version |
|---|---|---|
| Assembly | SPAdes (via Galaxy) | 4.2.0 (per-strain — confirm from the Galaxy history) |
| BGC detection | **antiSMASH** | 8.0.4 (core cohort) |
| Extraction at this inventory snapshot | Sapote-Mamey / Mamey | historical engine 1.9.135 / bundle 9.7.382; inspect the selected BUILD_STAMP for the active cut |
| Per-gene homology | BLAST+ blastp (Swiss-Prot local; nr web; EBI/UniProtKB) | 2.17.0+ |
| GCF network | BiG-SCAPE 2 (+ pyhmmer, Pfam-A, MIBiG) | 2.0.3 / MIBiG 4.0 |
| Figures | clinker / matplotlib / NumPy | clinker 0.0.32 |
| Phylogenomics | Prodigal, MUSCLE, trimAl, IQ-TREE 3, fastANI, GToTree, NCBI datasets | see inventory |

antiSMASH is **not guaranteed uniform** across every genome, so record the version per strain from
its own `manifest.json` before citing one in Methods. In this project the governed AS cohort and the
SID cohort are uniformly **8.0.4**; only the reference/type-strain comparison shelf (~11 organisms)
ran the unversioned dev build `8.dev-cf2fc5ee(changed)`, which must be footnoted, not cited as a
release, wherever those genomes appear in a figure.

These historical cohort/version declarations must be checked against each selected source before reuse. They do not establish current cohort membership or uniformity.
