# What Mamey reads from an antiSMASH output ZIP

Mamey's intake is **not GBK-only**. It reads several file types from an antiSMASH
output archive, each for a specific purpose. This page is the reference for what is
consumed and the one gotcha that silently thins your evidence.

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
| **Record JSON** — the large `*.json` | Opened only in `--json-evidence bounded` (default) or `full`. Carries **KnownClusterBlast (KCB)**, `region_to_region`, **RiQ** scores, and **TIGRFAM** diagnostics (`antismash.detection.tigrfam`). |
| **ClusterBlast / KnownClusterBlast TXT** — `knownclusterblast/*.txt`, `clusterblast/*.txt`, MIBiG txt | The **KCB / MIBiG reference-hit** source when JSON is `off` (the fallback path). Yields `mibig_reference_hits` and `clusterblast_ranked` organism hits. |
| **`.log`** | antiSMASH run log — metadata / version cross-check only. |

## `--json-evidence` modes

| Mode | Behaviour |
|---|---|
| `bounded` | **Default** for `run`. Streams the JSON with ijson, extracting only KCB / RiQ / TIGRFAM keys under record + byte caps. Never materialises the whole document. Falls back to `off` if ijson is missing, or **mid-run if the stream exceeds the wall-clock budget** (a `[WARN]` is logged). |
| `off` | Never opens the JSON. KCB comes from the TXT clusterblast files; **TIGRFAM is unavailable** (JSON-only). Fastest; safe for any genome size. Forced in capped / ChatGPT-safe runs. |
| `full` | Legacy: loads the whole JSON. Refuses files > 20 MB. Only for small JSON. |

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

## The one gotcha: a JSON-less ZIP degrades silently

KCB has **two provenance routes** — the JSON (`bounded`/`full`) or the TXT clusterblast
files (`off`). **TIGRFAM has only one — the JSON.** So:

- A **local antiSMASH CLI run** writes the record JSON; bounded gets full evidence.
- A **partial or web export of only region GBKs** has no JSON. Under `bounded` the engine
  finds nothing to stream and falls back to TXT-only KCB **with no TIGRFAM** — and, before
  v9.7.383, with no signal. As of v9.7.383 the intake **warns** when a `bounded`/`full`
  run meets a JSON-less ZIP (see `parsers._zip_has_record_json`).

**Recommendation:** keep `bounded` (the default) whenever evidence completeness matters —
it auto-demotes safely, so there is no robustness cost to leaving it on. Use `off` only
for a capped/ChatGPT-safe run or a strain whose JSON is known to be pathological, and
know you are then forgoing TIGRFAM. When you download from the antiSMASH web server,
take the **full results archive**, not just the region GBKs, or bounded has no JSON to read.

## The external tools that produce these inputs

Mamey is stage 3 of a longer pipeline. Upstream and downstream tools (with the versions
of record) are catalogued in the project's tool inventory; the essentials:

| Stage | Tool | Version |
|---|---|---|
| Assembly | SPAdes (via Galaxy) | 4.2.0 (per-strain — confirm from the Galaxy history) |
| BGC detection | **antiSMASH** | 8.0.4 (core cohort) |
| Extraction (this engine) | Sapote-Mamey / Mamey | engine 1.9.135 / bundle 9.7.382 |
| Per-gene homology | BLAST+ blastp (Swiss-Prot local; nr web; EBI/UniProtKB) | 2.17.0+ |
| GCF network | BiG-SCAPE 2 (+ pyhmmer, Pfam-A, MIBiG) | 2.0.3 / MIBiG 4.0 |
| Figures | clinker / matplotlib / NumPy | clinker 0.0.32 |
| Phylogenomics | Prodigal, MUSCLE, trimAl, IQ-TREE 3, fastANI, GToTree, NCBI datasets | see inventory |

antiSMASH is **not guaranteed uniform** across every genome, so record the version per strain from
its own `manifest.json` before citing one in Methods. In this project the governed AS cohort and the
SID cohort are uniformly **8.0.4**; only the reference/type-strain comparison shelf (~11 organisms)
ran the unversioned dev build `8.dev-cf2fc5ee(changed)`, which must be footnoted, not cited as a
release, wherever those genomes appear in a figure.
