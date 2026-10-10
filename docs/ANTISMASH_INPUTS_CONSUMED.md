# What Mamey reads from an antiSMASH output ZIP

Mamey's intake is **not GBK-only**. It reads several file types from an antiSMASH
output archive, each for a specific purpose. This page is the reference for what is
consumed and the evidence gaps that can arise from partial inputs or limited reads.

Only regular ZIP file members are eligible as data. Finder metadata (`__MACOSX/`,
AppleDouble `._*` sidecars, and `.DS_Store`) is also excluded from the data namespace.
Directory entries are structural, and Unix special members (including symlinks, devices,
FIFOs, and sockets) are ignored by archive inspection and parsing even when their names end
in `.gbk`, `.json`, or another recognized suffix. Extraction helpers refuse special members
before writing any archive data.

## Files consumed, by role

| File in the antiSMASH ZIP | Role in Mamey |
|---|---|
| **Region GBK** — `*.regionNNN.gbk` (also `.gbff`/`.gb`) | **Primary source.** Each region GBK → one `BGCRecord`: per-CDS `/gene_functions`, `sec_met_domain` (Pfam/domain hits **+ E-value**), `aSDomain`, `smCOG`, product labels, coordinates. The ten source-derived scans run over these parsed records. |
| **Whole-record / genome GBK** | antiSMASH **version** detection, original region bounds, contig-length map (edge/fragment flags). |
| **FASTA** — `.fasta/.fa/.fna/.ffn` | **Assembly metrics** — contig count, N50, total length, contig-length lookup. Not scanned for BGC content. |
| **Record JSON** — the large `*.json` | The main evidence walker reads this in `--json-evidence bounded` (default) or `full`. Independent metadata and record readers can still inspect JSON in `off`. Carries **KnownClusterBlast (KCB)**, `region_to_region`, **RiQ** scores, and **TIGRFAM** diagnostics (`antismash.detection.tigrfam`). Separate requested record readers also collect supported module predictions, RiPP motif cores and RRE-Finder rows; see [saved RiPP evidence](#saved-ripp-motif-evidence). |
| **ClusterBlast / KnownClusterBlast TXT** — `knownclusterblast/*.txt`, `clusterblast/*.txt`, MIBiG txt | The **KCB / MIBiG reference-hit** source when JSON is `off` (the fallback path). Yields `mibig_reference_hits` and `clusterblast_ranked` organism hits. |
| **`.log`** | Metadata/version cross-check and the recognized record-cap coverage probe. Keep actual logs and run settings; no matched cap message does not prove complete scanning. |

## `--json-evidence` modes

| Mode | Behaviour |
|---|---|
| `bounded` | **Default** for `run`. Streams the JSON with ijson, extracting only KCB / RiQ / TIGRFAM keys under record + byte caps. Never materialises the whole document. Falls back to `off` if ijson is missing, or **mid-run if the stream exceeds the wall-clock budget** (a `[WARN]` is logged). |
| `off` | Skips the main KCB/RiQ JSON walker; independent version, strictness, original-bounds and other record paths can still read JSON. KCB comes from the TXT clusterblast files; **TIGRFAM is unavailable** (JSON-only). Reduces this walker’s work; does not remove all input/resource constraints. Forced in capped / ChatGPT-safe runs. |
| `full` | Legacy: loads the whole JSON. Refuses files over 80,000,000 bytes (`FULL_MAX_JSON_BYTES`). Only for small JSON. |

## Bounded RiQ record identity

RiQ scores are bound to the full `records[]` record `id` and region number only
after that record closes. JSON field order does not matter: `id` may follow
`modules`. Missing, blank, non-string, or duplicate `id` fields do not borrow an
identity from another record. Scores outside a record, or observed in a record
interrupted by a parse error or the leaf cap, remain unassigned in `loose_hits`.
Unassigned record scores retain a maximum and `riq_observation_count` per region,
with a `riq_identity_status` explaining the missing binding. They do not enter
the mapped genome RiQ summary or a per-locus score.

This is source-record binding, not a substitute for the complete displayed locus
identity: `strain / full node-or-contig / region / BGC alias`. It does not change
the existing JSON size/leaf caps, other evidence extractors, or the claim ceiling:
RiQ is similarity evidence, never proof of product identity or activity.

## Partial input and bounded-reader gaps

KCB has **two provenance routes** — the JSON (`bounded`/`full`) or the TXT clusterblast
files (`off`). **TIGRFAM has only one — the JSON.** So:

- A complete local antiSMASH export can include record JSON; bounded attempts the supported evidence under caps, not guaranteed full coverage.
- A **partial or web export of only region GBKs** has no JSON. Under `bounded` the engine
  finds nothing to stream and falls back to TXT-only KCB **with no TIGRFAM** — and, before
  v9.7.383, with no signal. As of v9.7.383 the intake **warns** when a `bounded`/`full`
  run meets a JSON-less ZIP (see `parsers._zip_has_record_json`).

**Recommendation:** keep `bounded` (the default) whenever evidence completeness matters —
it records caps, truncation, parse warnings and fallback states; inspect those before treating evidence as complete. Use `off` only
for a capped/ChatGPT-safe run or a strain whose JSON is known to be pathological, and
know you are then forgoing TIGRFAM. When you download from the antiSMASH web server,
take the **full results archive**, not just the region GBKs, or bounded has no JSON to read.

## Saved RiPP motif evidence

Request **read saved RiPP motif evidence** with the reviewed package, its producing source ZIP/hash and a complete `strain / full node-or-contig / region / BGC alias`. This is an inspection request, not a separate registered RiPP companion command or an instruction to run a new predictor.

The record extractor iterates `antismash.modules.<family>` entries whose `motifs` field is a nonempty dictionary. It accepts motif dictionaries containing a truthy `core` or `core_sequence`, and preserves module family, record ID, locus tag, motif index, leader/tail and raw motif details. The old four-family tuple is not the active family limit. Unsupported shapes or entries without a core are skipped; acceptance here does not validate an amino-acid alphabet, cleavage site, mature product or biochemical function. Compare saved rows with their exact source motif objects before interpretation.

During package authoring, normalized rows are written to `<strain>_3_antismash_ripp_motifs.csv` and `<strain>_3_antismash_structured.json`, and to workbook sheet `antiSMASH_RiPP_Motifs`. Inspect `mapping_status`, `mapping_method`, `source_file`, `locus_tag`, `core_sequence` and `detail_json`. Coordinates can come from JSON, its motif location or matched CDS geometry. Missing or multiply overlapping geometry remains unmapped/ambiguous; a nonblank core alone does not resolve the full locus.

The JSON mode label is not the complete RiPP read contract. Record extras are requested when the original requested mode is not `off`, or when the caller explicitly includes structured evidence; the main bounded walker can fall back separately. Inspect actual reader warnings, normalized counts and saved source status. Structured `PASS` requires some structured table to have rows, not RiPP-specific coverage; an empty RiPP table can coexist with other populated tables. `NULL_NO_STRUCTURED_ANTISMASH_EVIDENCE` or an error state does not establish biological absence. Review exact source coverage and typed holds before using an empty table as a no-call.

## Historical external-tool inventory (not current environment validation)

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

## Scope, identity and partial reads

Suffix support is parser-specific. Main GenBank intake supports `.gbk/.gbff/.gb`, filters regular members and Finder metadata, and prefers region records with a whole-record fallback (`mamey/parsers.py:343–389,756–770`). It may encounter missing/unparseable records; a filename count is not a successful-CDS/BGC census. Region-only inputs without true contig-length evidence carry unknown boundary information rather than inventing whole-genome geometry. Multiple parsed records and generated alias order must be reconciled to the actual inventory; never join by a bare BGC alias.

Bounded main evidence uses streaming when available, with byte and leaf caps, and can retain partial/unassigned observations. `BOUNDED_MAX_RECORDS_STREAMING=200000`, `BOUNDED_MAX_JSON_BYTES_STREAMING=250000000`, and full mode's 80000000-byte limit apply to that reader, not overall RAM or all source-record reads (`mamey/antismash_evidence.py:129–146,987–1223`). A refused/partial reader is not biological absence. Read per-channel availability and truncation fields rather than treating the configured mode as completed coverage.

The CLI's main-walker budget defaults to 300 seconds through `MAMEY_BOUNDED_BUDGET_S`; 0 disables it. On platforms without SIGALRM the guard is unavailable, recorded as `RETURNED_GUARD_UNAVAILABLE` (`mamey/cli.py:319–335,1423–1426`). This is not a universal run timeout. Version/profile metadata probing remains independent (`mamey/parsers.py:122–187`, `mamey/antismash_input.py:185–203`). See [strictness provenance](ANTISMASH_PROFILE.md).

The inventory and cohort uniformity statements above are historical project observations, not current input bindings. Confirm each actual archive/version/hash before reusing them in methods or figures. Retain extraction and environment-validation receipts for the selected inputs separately.

## antiSMASH record-cap coverage

The `.log` reader checks for an antiSMASH record-limit message separately from JSON evidence caps. If it recognizes the message, the run adds `RECORD_LIMIT_TRUNCATION` to its issues: the supplied region inventory covers the analyzed records, while submitted FASTA or whole-record assembly statistics may cover a larger input. Package completion does not establish equal coverage between these fields.

Read `analysed`, `first_skipped` and `skipped_count` as parsed log observations. The detector recognizes `Only analysing the first N records` (also lowercase initial `only`) and counts matching skip-message occurrences in the first matching regular `.log` member. Repeated lines can increase `skipped_count`; it is not a deduplicated skipped-record inventory. A header can trigger truncation with zero recognized skip lines. Different archived logs, changed wording or absent log messages require source review.

A returned `truncated=False` means this detector did not recognize the pattern. It does not prove that all eligible records were scanned: no log, an unreadable ZIP, unreadable log members or an unmatched message can produce that result. When an exception escapes the helper, the CLI emits `RECORD_LIMIT_PROBE_FAILED` and an ERROR phase receipt; failures handled inside the helper do not reach that error route. Preserve actual archive/hash, run configuration, logs and scanned/skipped record inventory before making completeness or absence claims.

The generated truncation warning describes full-FASTA statistics, but input metrics can instead come from a GenBank fallback or remain unavailable. Check the actual FASTA/whole-record/region source universe before quoting the warning. See [assembly metric and warning scope](reference/06_CURRENT_SOURCE_SCOPE.md#volume-ii-b4-assembly-input-scope-independent-tier-fields-and-warning-limits). Retain the existing input and output as evidence; if complete coverage is required, plan a separate authorized upstream run after checking its inputs and installed antiSMASH options. Changing an extraction JSON mode does not recover regions never analyzed upstream.

## Carry coverage warnings into summaries

Read the full `manifest.json` issues, `commit_receipt.json` issues and `issue_log.md` alongside the original input/log evidence. These outputs carry the supplied issue strings; they do not serialize the complete `_trunc` or `_sanity` helper dictionaries with an explicit source-record roster. A success-shaped or quiet summary therefore cannot supply a missing log binding, distinct skipped-record inventory or verified assembly universe.

The compact manifest, per-strain workbook and brief are narrower views. Do not assume that their displayed raw count, weighted count or assembly tier carries every record-limit warning or probe-failure state. Resolve the actual input scope and retain any unavailable, unreadable or unrecognized detector state before comparing strains or quoting a whole-genome count. For an individual locus, retain `strain / full node-or-contig / region / BGC alias` and its same-input source provenance.

When a probe fails, keep the ERROR row from `run_phase_receipts.jsonl` with the warning and native attempt identity. When the record-cap helper handles a read failure internally, an ERROR row may not exist; absence of that row is not successful coverage. Preserve the original evidence and obtain a separately authorized upstream result only when the intended coverage requires it.

Sources: `mamey/parsers.py:1045–1080`, `mamey/cli.py:2052–2132,2667–2696,3905–3921`, `mamey/models.py:504` and the shared regular-member selector in `mamey/ziputil.py`.
