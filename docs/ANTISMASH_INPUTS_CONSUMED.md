# What Mamey reads from an antiSMASH ZIP

Check what evidence your ZIP can supply and find its saved result files. Use the
full antiSMASH result archive and an installed program. From the program folder,
replace this example path with your ZIP:

```bash
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
```

Read the version and counts of GenBank, JSON and comparison files. The inspector
reports file types and counts, rather than individual filenames. Use
[Your first run](reader/01_FIRST_RUN.md) for the analysis commands.

<a id="scope-identity-and-partial-reads"></a>

## What each file supplies

- **Region GenBank:** region/CDS records, product labels, coordinates and domains.
  Duplicate screening can make the file count differ from the record count.
- **Whole-record GenBank:** original region bounds, contig lengths, version and
  fallback assembly statistics when FASTA is absent.
- **FASTA:** assembly statistics, including contig count, N50 and total length.
- **Record JSON:** comparisons, RiQ scores, TIGRFAM, modules, RiPP motifs and RRE-Finder evidence.
- **ClusterBlast/KnownClusterBlast text:** reference and ranked-organism hits,
  read before JSON in every evidence mode.
- **antiSMASH log:** version cross-check and record-cap detection.

Assembly statistics use FASTA first, then full-record GenBank. A region-only ZIP
lacks whole-genome input: zero assembly counts mean missing input, and contig
lengths may be unknown. Use **strain / full node-or-contig / region / BGC alias**
to join records.

## Read saved RiPP motif evidence

In `runs/EXAMPLE/package/`, open `AS-40_5_workbook.xlsx` and select
`antiSMASH_RiPP_Motifs`. The same rows are in `AS-40_3_antismash_ripp_motifs.csv`
and `AS-40_3_antismash_structured.json`.

Read the mapping status, source file, locus tag, core sequence and details.
A gene can have several predictions; count rows and distinct gene tags separately.
Missing or overlapping coordinates remain unmapped or ambiguous. A saved core is
an antiSMASH prediction; inspect it before interpreting cleavage or mature product.

Structured `PASS` means at least one structured table has rows. Read the RiPP row
count itself to see whether motif evidence was found.

<a id="antismash-record-cap-coverage"></a>

## Check coverage before comparing strains

The log probe looks for antiSMASH cap/skip messages. `TRUNCATION_OBSERVED` records
a cap message; `NOT_DETECTED` means a recognized log was read without one.
`UNAVAILABLE`, `UNRECOGNISED_LOG` and `FAILED` leave coverage unverified.
A probe exception records `RECORD_LIMIT_PROBE_FAILED` and an error phase row.

`skipped_count` counts matching log lines, so repeats can inflate it. A cap header
without skip lines still signals truncation. Changing JSON mode cannot recover
regions antiSMASH never analyzed.

<a id="carry-coverage-warnings-into-summaries"></a>

Read the full issue lists in `manifest.json`, `commit_receipt.json` and
`issue_log.md` before quoting a genome-wide count. Compact summaries and briefs
may omit coverage warnings.

## Optional: change JSON reading

The default, `bounded`, streams the main walker under byte and stored-leaf limits.
Keep it for the first run.

`--json-evidence off` skips that walker. KCB text and separate metadata/record
readers can still supply evidence. `--capped-session` forces this mode; check
channel statuses to see which readers ran. Structured record reads run when JSON
mode is not off or structured evidence is requested.

`--json-evidence full` loads the whole JSON and refuses an individual uncompressed
file over 80,000,000 bytes. The compressed ZIP size is not that limit.

<a id="partial-input-and-bounded-reader-gaps"></a>

If the ZIP has no record JSON, the main walker has nothing to stream. KCB can come
from text, but JSON-derived TIGRFAM is unavailable. Intake warns for bounded/full
runs without record JSON. Check the full archive before changing modes.

<details>
<summary>Reader limits and RiQ mapping</summary>

Bounded mode needs `ijson`; without it, the main walker records `json_skipped` and
falls back to off. It skips members above 250,000,000 uncompressed bytes. The
200,000-leaf cap limits stored auxiliary evidence, not the record walk for RiQ.

The default bounded budget is 300 seconds and includes separate record passes.
`MAMEY_BOUNDED_BUDGET_S` changes it; zero disables it. An overrun retries in off,
which can still read TIGRFAM. Systems without `SIGALRM` record
`RETURNED_GUARD_UNAVAILABLE`. This budget is not a whole-run time or RAM limit;
other readers have separate limits and full-load fallbacks.

<a id="bounded-riq-record-identity"></a>

RiQ scores attach to the full JSON record ID and region after the record closes.
Missing, repeated or invalid IDs and interrupted records leave scores unassigned.
Their per-region maximum, observation count and identity status stay in
`loose_hits`, excluded from genome/locus scores. Separate RiQ caps can limit counts
or member mapping.

Finder metadata is ignored; special archive members such as symlinks and devices
are skipped by readers or refused by extraction helpers.

</details>

<a id="historical-external-tool-inventory-not-current-environment-validation"></a>

## Record the antiSMASH version

Read each strain's version from its own archive and manifest, and keep the source
hash. Record a development build as a development build. Use the selected bundle's
version for Mamey, and [antiSMASH strictness](ANTISMASH_PROFILE.md) for detection settings.
