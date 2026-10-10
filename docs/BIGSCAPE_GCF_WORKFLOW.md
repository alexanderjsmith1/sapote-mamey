# BiG-SCAPE GCF workflow — resumable, source-preserving companion analysis

Before any `doctor` example below, read the [write-probe boundary](INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

**Authority:** read `docs/LLM_COMPANION_TOOL_PROTOCOL.md` first. This is the active BiG-SCAPE
runbook. Cohort-specific guides and older version addenda do not override it.

For a command-by-command cohort example using the bundled launcher and figure tools, see the
[cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

BiG-SCAPE groups antiSMASH region GBKs by domain architecture and related sequence features.
It is a downstream companion analysis: it does not alter the sealed Mamey run, and its families are
run-specific similarity groups rather than compound identities.

## 1. Input contract

Use antiSMASH **region GBKs**, not whole-genome FASTA and not Mamey CSV rows. Region GBKs may be
read directly from the antiSMASH ZIP; do not require the user to duplicate/extract them manually.

For every staged member record:

- source ZIP path and SHA-256;
- archive member path, uncompressed bytes, and member SHA-256;
- strain, BGC ID, and `contig·region` locator;
- antiSMASH version when recoverable;
- whether the record is cohort or reference.

Skip macOS AppleDouble members (`__MACOSX/` and basenames beginning `._`). Quarantine malformed or
colliding locators. Store one content-addressed object and expose strain-prefixed relative links in
the run's `input_view/`.

## 2. Preflight and approval boundaries

Probe without mutating inputs:

```bash
python mamey_run.py doctor --companions
bigscape --version
hmmscan -h | head
FastTree -help 2>&1 | head
```

Confirm that `Pfam-A.hmm` exists and that its pressed companions (`.h3f`, `.h3i`, `.h3m`, `.h3p`)
match it. Record hashes and file sizes. BiG-SCAPE 2.0.3 may call lowercase `fasttree` even when a
conda environment ships only `FastTree`; test both names before the run. If necessary, create a
run-local lowercase symlink and record it as a recovery action. Do not modify the environment
silently.

MIBiG is optional. Never auto-download it. State whether the planned run is:

- `cohort-only` — valid for within-run family sharing; no known/novel language;
- `cohort-plus-MIBiG` — reference-panel anchoring, with MIBiG version and hashes;
- `reference-augmented` — other reference GBKs, with their provenance.

Show the user the preflight fields required by the authoritative protocol. Network/reference
acquisition and canonical ingest require explicit approval.

## 3. Canonical cohort run

Use BiG-SCAPE 2.x subcommand syntax and preserve the exact `--help` output/version in the run
receipt. The command below is a template; first reconcile option names against the installed 2.x
version:

```bash
bigscape cluster \
  -i <run>/input_view \
  -o <run>/outputs \
  -db <run>/outputs/bigscape.db \
  -p <absolute-path>/Pfam-A.hmm \
  --record-type region \
  --classify category \
  --gcf-cutoffs 0.3,0.5,0.7 \
  --include-singletons \
  -c 1
```

If the installed CLI uses different spelling, the locally verified command is authoritative and
must be captured in `COMMAND.sh` and `RUN_MANIFEST.json`. One core is the interactive default; two
is balanced; four is the surfaced ceiling.

**Alignment mode — leave it on the default `auto` for this cohort, and say so.** BiG-SCAPE compares a
pair of clusters with *global* alignment when both are complete and *glocal* when at least one is
fragmented; 2.0 adds a true *local* mode for divergent pairs that share only a domain subset. The
default `auto` selects global/glocal per pair and is the correct behaviour for the bee/wasp cohort,
whose assemblies are often fragmented — do **not** force `global`, which the tool documents as
appropriate only for datasets with no contig breaks and manually curated borders. Verify the exact
flag name against the installed `bigscape cluster --help` and record the chosen mode in the receipt.
See §8 for why this matters here.

Do not pass a MIBiG flag or reference directory to a cohort-only run. In the locally verified
BiG-SCAPE 2.0.3 interface, `-m/--mibig-version` can acquire/select MIBiG and is therefore a networked,
user-approved action; `-r/--reference-dir` is for explicit user-defined non-MIBiG references. For an
approved reference run, record every reference object and exact flag. MIBiG files
often do not contain `region` or `cluster` in their filenames, so confirm the reference load count;
never infer successful loading from the presence of a path.

## 4. Resume and recovery

Before retrying, inspect `RUN_STATE.json`, log tail, database integrity, completed database run rows,
and cached record counts. Resume the same run only when inputs and scientific parameters are
unchanged. Record operational repairs, such as a `fasttree` alias, in `EVENTS.jsonl` and the state.

Do not create parallel databases and later join them by `family.id`. Family IDs and viewer
`FAM_#####` labels are local to a particular database/run. If reference batches must be processed
separately, join only on portable biological keys and reference accessions, retaining the source run
for every edge.

## 5. Exact-run QA and export

SQLite may contain failed and completed historical rows. Select the completed run using state,
parameters, timestamps, and expected memberships; never use `max(run.id)` as a proxy for “current.”
Record the chosen ID.

QA must report, at minimum:

- manifested/staged/database GBK counts;
- strain and locator coverage, collisions, and exclusions;
- CDS, domain-hit, distance, family, and membership counts;
- family counts and membership denominators at 0.3, 0.5, and 0.7;
- database integrity result and nonzero exit status history;
- output-file and portable-export checksums;
- whether references were genuinely loaded.

Create a portable table keyed by cutoff, source run ID, strain, BGC ID, and `contig·region`.
Family ID may be included for display but cannot be the cross-run join key.

## 6. Interpretation and optional reconciliation

For a cohort-only run write, for example:

> AS-XXX NODE_…·region… and AS-XXX NODE_…·region… were assigned to the same run-specific
> BiG-SCAPE family at cutoff 0.5 (run 3). This supports related BGC architecture in the sampled
> cohort; it does not establish compound identity, production, activity, or novelty.

Only a user-approved, source-preserving reconciliation may add this context to Mode B cards or the
triage board. Write overlays or copied deliverables by default; never silently edit sealed/canonical
cards. Preserve the original hash, the exact completed BiG-SCAPE run ID, cutoff, and portable key.

## 7. Minimum deliverables

- `RUN_MANIFEST.json`, `RUN_STATE.json`, `COMMAND.sh`, `EVENTS.jsonl`, and `HANDOFF.md`;
- database plus integrity receipt;
- exact-run family/membership TSV;
- cross-strain portable TSV;
- HTML/network/tree outputs that actually exist;
- `QA_REPORT.json` and SHA-256 manifest;
- a limitations/claim-ceiling note.

BiG-SCAPE completion is not Mamey release approval, biological validation, or publication readiness.

## 8. Fragmentation and contig edges (this cohort)

The bee/wasp cohort has many fragmented assemblies (some VERY_POOR: e.g. AS-XXX, AS-XXX), so a BGC is
frequently split across contigs or sits on a contig edge. That changes how GCF results must be run and
read — and it is the single most important interpretation caveat for this cohort.

**What fragmentation does to GCFs.** A pathway split across two contigs presents to BiG-SCAPE as two
short, partial records. Under global alignment they look divergent and land in *separate, weak*
families; a genuinely single novel cluster is then double-counted and under-supported. Under
glocal/local, a fragment can align to the matching subset of its complete cognate and cluster with it.

**Run settings for this cohort.**
- **Mode = default `auto`** (global for complete pairs, glocal when either is fragmented). Do not force
  `global` (§3). Consider the 2.0 `local` mode when comparing a short fragment against a divergent but
  domain-sharing reference; record which mode was used.
- **`--include-singletons`** (already in the §3 template): keep un-familied fragments as visible nodes.
  Retain lone fragments visibly while recording whether they were compared and whether any
  reference panel was loaded; singleton status does not supply novelty evidence.
- **Multi-cutoff** (0.3/0.5/0.7): fragments merge/split with stringency; report the denominator at each.

**Reading and reporting.**
- antiSMASH marks `on_contig_edge`; **carry that flag into every GCF-based count** and caveat it. Edge
  BGCs are expected to under-cluster; a small or singleton family that is all edge records is a
  possible fragmentation effect requiring review, not proof of artifact or biological rarity.
- **Cross-check split families against RG-GMCI.** Where two weak same-strain families each hold half of
  a pathway, the engine's RG-GMCI cross-contig linkage (two-proof: homology **and** biosynthetic-logic
  complementarity) provides candidate evidence for reviewing a possible split cluster. Reconcile exact identities and
  receipts before proposing a combined count; neither a group label nor increased reference coverage
  establishes physical linkage or owner acceptance.
- **Concordance with the Mamey pangenome** (`COHORT_domain_architecture_by_bgc.csv`) is a consistency check under matched input and scope;
  disagreement can reflect fragmentation, annotation, thresholds, input scope or reference-panel
  differences. Inspect those alternatives rather than assigning fragmentation as the cause.

**Claim-safety.** None of this upgrades a fragment to a claim. A fragmented GCF is capacity consistent
with a family in the *sampled cohort*; it is never compound identity, production, activity, or a
confident novelty/rarity count. Note assembly quality wherever a fragmented record drives a number.

## 8.1 Historical panel illustration: singleton and cohort-private scope

The following numerical examples are historical contributor-lane observations (2026-08-03),
not denominators for a new run. Their source database identities/hashes and completed-run receipts
must be recovered before reuse. Apply the panel-scope principle without transferring the numbers:

- **Denominator.** Only `record_type = region` rows are eligible for a family. Sub-records
  (`cand_cluster` / `protocluster` / `proto_core`) are the same regions at finer granularity and were
  never candidates. Build assignment/singleton rates on the **region** denominator, never the total
  `bgc_record` count.
- **Unassigned requires a comparison-state check.** `--include-singletons` expresses the intended
  output policy; it does not prove each region was scanned, compared and assigned in the selected
  completed run. Distinguish a measured singleton from failed, excluded, unbound or unmeasured
  records. Absence of a distance row is not evidence of biological privacy; verify the selected
  run membership and comparison coverage before counting.
- **A high cohort-private / singleton rate is usually panel composition, NOT biology and NOT
  fragmentation.** Measured example: AS regions are GCF-singletons at ~3× the SID rate (65.3% vs 19.7% at
  cutoff 0.3), and the gap **widens** on interior (non-truncated) regions only — so fragmentation is not
  the driver. The driver is that a mutually-redundant single-genus panel (e.g. 89 cohort *Streptomyces*)
  self-clusters trivially, while a multi-genus panel gives each BGC far fewer eligible within-panel
  neighbours.
- **Caption rule.** "cohort-private", "AS-private", "singleton", and "reference-dark" all describe **the
  panel and the reference set**, never the organism. They are **not** rarity or novelty. A private/dark
  count becomes a novelty *candidate* only with genus-matched comparators (sign-off gate #4 comparator
  provenance, #7 sampling) and low-identity ClusterBlast/RefSeq — cohort-privateness alone never suffices.
- **Do NOT use GCF-singleton as a novelty criterion in this panel.** It fires on ~2/3 of AS BGCs (base
  rate ~65%), so "lead X is also a singleton" is base-rate agreement, not independent corroboration
  (lift ≈1.5×). The *informative* direction is the **inverse**: a reference-dark lead that *does* have
  cohort neighbours sits in the ~35% minority and is worth a second look. (a contributor lane, 2026-08-03.)

## Implemented adapters versus the requested runbook

The manifest, content-addressed storage, member hashes, state/events and QA receipts above are requirements for a reviewed companion run; they are not all produced automatically by `tools/bigscape_prep.py` or `tools/bigscape_pipeline.py`. The prep tool writes GBK byte copies with strain-prefixed basenames and a strictness manifest, not content-addressed objects plus relative links. Its only per-record source hashes are for excluded small query records. Accepted staged records need a separate source-member/hash/identity roster. Record reason and estimated size before staging substantial data; retain source archives in place and avoid full-package duplication.

Prep requires explicit strictness or an explicitly justified mixed-input override, refuses a nonempty output directory, skips hard-excluded strains by default and returns1 for no staged records. Input-level errors are caught and reported; files staged earlier in a failing input can remain even when its manifest count is0. A successful aggregate count is not full manifest/filesystem parity. Collisions refuse a destination but do not roll back earlier records. Inspect exclusions, errors and all actual objects before clustering (`tools/bigscape_prep.py:98–109,149–209,266–327`).

The pipeline currently invokes prep without passing its required strictness/override options, so its normal prep path is refused by that front door. This is a code integration hold, not permission to bypass the input policy. A separately reviewed prepared input with `--skip-prep` is an alternative only when its complete provenance is already bound. `--skip-cluster` requires an explicit run ID. Pre-existing databases require one too; chunked MIBiG remains refused. Fresh runs infer exactly one new run-ID row, but that delta alone does not certify completed scientific results or expected reference loading (`tools/bigscape_pipeline.py:112–126,145–218`).

The pipeline invokes known/novel and cross-strain exporters even on its no-MIBiG branch. Their presence and legacy status strings do not authorize known/novel language on a cohort-only run. Its optional ingest mutates cards; it is not an additive overlay implementation and does not generate the complete minimum-deliverables receipt set. Follow [integration limitations](BIGSCAPE_MAMEY_INTEGRATION.md) and the [reader recovery guide](troubleshooting/BIGSCAPE_TROUBLESHOOTING.md) before interpreting or reconciling outputs. Bind the selected run logs and output hashes before using an external result.
