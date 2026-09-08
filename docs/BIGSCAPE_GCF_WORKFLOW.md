# BiG-SCAPE GCF workflow — resumable, source-preserving companion analysis

**Authority:** read `docs/LLM_COMPANION_TOOL_PROTOCOL.md` first. This is the active BiG-SCAPE
runbook. Cohort-specific guides and older version addenda do not override it.

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
  A lone fragment must not silently vanish from the network — it is often exactly a reference-dark
  novelty candidate.
- **Multi-cutoff** (0.3/0.5/0.7): fragments merge/split with stringency; report the denominator at each.

**Reading and reporting.**
- antiSMASH marks `on_contig_edge`; **carry that flag into every GCF-based count** and caveat it. Edge
  BGCs are expected to under-cluster; a small or singleton family that is all edge records is a
  fragmentation artefact to flag, not a biological "rare family" claim.
- **Cross-check split families against RG-GMCI.** Where two weak same-strain families each hold half of
  a pathway, the engine's RG-GMCI cross-contig linkage (two-proof: homology **and** biosynthetic-logic
  complementarity) is the arbiter of whether they are one split cluster. Reconcile the BiG-SCAPE view
  against RG-GMCI before counting families for a fragmented strain, and prefer the RG-GMCI verdict for
  same-strain cross-contig pairs.
- **Concordance with the Mamey pangenome** (`COHORT_domain_architecture_by_bgc.csv`) is strong evidence;
  families that disagree between BiG-SCAPE and the pangenome are exactly where fragmentation is biting —
  look there, and caveat.

**Claim-safety.** None of this upgrades a fragment to a claim. A fragmented GCF is capacity consistent
with a family in the *sampled cohort*; it is never compound identity, production, activity, or a
confident novelty/rarity count. Note assembly quality wherever a fragmented record drives a number.

## 8.1 "Singleton" / "cohort-private" is a statement about the panel, not the organism

A cross-run analysis (a contributor lane, 2026-08-03: `full_cohort.db` × `domain_knowledge.sqlite`) makes a
caption rule mandatory for every GCF-derived count:

- **Denominator.** Only `record_type = region` rows are eligible for a family. Sub-records
  (`cand_cluster` / `protocluster` / `proto_core`) are the same regions at finer granularity and were
  never candidates. Build assignment/singleton rates on the **region** denominator, never the total
  `bgc_record` count.
- **"Unassigned" = singleton, not unclustered.** With `--include-singletons` the region was scanned and
  compared; it simply has no partner within the cutoff. Exception: a handful of regions carry **no
  distance row at any cutoff** — they were never compared, so "singleton" there rests on the *absence of
  a comparison* (weaker) and must not be counted as evidence.
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
