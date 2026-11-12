# BiG-SCAPE troubleshooting

Symptoms first, then the cause and the fix.
Walkthrough: [cohort walkthrough](../BIGSCAPE_COHORT_WALKTHROUGH.md). Rules: [cohort workflow](../BIGSCAPE_GCF_WORKFLOW.md). For exact reader selection, skipped or failed outputs and recovery receipts, read [BiG-SCAPE reader recovery](../../tools/BIGSCAPE_READER_RECOVERY.md).

## Launcher preflight and writes

The launcher is `tools/bigscape_launch.sh`. It does not create or install the BiG-SCAPE environment. Before each run:

1. Set `BIGSCAPE_ENV_BIN` (the environment's `bin` folder) and `PFAM_HMM` (the pressed `Pfam-A.hmm`).
2. Use a fresh output folder. The launcher overwrites `<out>/run.log`. It names the database `<out>/<label>.db`, and the default label is `run_<today's date>`. A second run on the same day in the same folder points at the same database file.
3. Pass `--cores 1`. The launcher defaults to four cores. The walkthrough starts with one.
4. The launcher checks that `Pfam-A.hmm` and all four pressed files (`.h3f`, `.h3i`, `.h3m`, `.h3p`) exist, and exits 2 if one is missing. It does not check that they were pressed from this `Pfam-A.hmm`.
5. Keep the command, the exit status, the complete log, and the input, tool and database hashes. The version and count lines the launcher prints are not a completion receipt.
6. With `--mibig-dir`, record the previous link target first (see below).

`--mibig-dir` invokes `ln -sfn` on a slot inside the installed BiG-SCAPE package (`MIBiG/mibig_antismash_<name>_gbk`) before checking its count. Inspect the destination type, contents and current target first: an existing real directory can receive a link inside it instead of becoming the requested symlink. Changes can remain after a refusal. Use only an environment you are authorized to change; do not remove or replace existing contents without authority. Verify the resolved slot afterward.

`--mibig-name` is a chosen label, for example `local2088`. The launcher requires at least 2,000 paths matching `*.gbk` under the resolved slot, not necessarily `BGC*.gbk` or independently verified MIBiG identities. Exit 3 reports a lower count. Bind the intended reference inventory and hashes separately; this threshold neither verifies the inventory nor counts references supplied through other routes.

Launcher exit codes:

| Code | Meaning |
|---|---|
| 0 | BiG-SCAPE exited 0 (and, with `--mibig-dir`, the log proved a positive MIBiG count). |
| 2 | Setup error: `bigscape` not executable, Pfam not pressed, `fasttree` missing, an unknown argument, a missing input folder, no GBKs in it, or `--mibig-dir` without `--mibig-name`. |
| 3 | The MIBiG folder holds fewer than 2,000 GBKs. |
| 4 | `--mibig-dir` was given but the log did not show a positive loaded MIBiG count. |
| 5 | BiG-SCAPE itself exited nonzero; its own code is printed as `BIGSCAPE_EXIT=N`. Read `<out>/run.log`. |

The explicit launcher refusals listed above print a `LAUNCHER_STAGE` marker (`setup`, `mibig_slot`, `mibig_count` or `bigscape`). Shell and other setup failures may exit differently and lack a marker; retain complete stderr and exit status. Diagnose from the command, environment and available log, not the number alone.

## The run

**`FileNotFoundError: fasttree` (or hmmsearch, diamond) after hours of clustering.**
A possible cause is an absolute-path invocation without the required environment on PATH. Check the failing executable, installed version and full traceback rather than assuming this cause or stage. A failed run can leave an incomplete database. Keep the log and the database before you decide whether a recovery is possible.
Fix: run through `tools/bigscape_launch.sh`. It puts the environment's bin folder on PATH and refuses to start without
`fasttree`. For a separately authorized direct invocation, put the selected environment bin directory on PATH, for example `export PATH="/path/to/environment/bin:$PATH"`, substituting its real path.

**`Loading 0 mibig GBKs` although you asked for MIBiG.**
This launcher supplies MIBiG through `-m` and the package slot described above. Check the slot type and resolved inventory, then the actual loaded counts. A dead link or filename filter can leave the intended references unrepresented; alternative reference inputs and inclusion filters depend on the installed version. Consult that version's documentation and verify its admitted reference roster rather than treating a count or filename convention as proof.

For this launcher, set `--mibig-dir` and `--mibig-name` only after the authorized slot review above. Its input threshold counts all matching `*.gbk` paths. If BiG-SCAPE exits 0 but the log does not prove a positive MIBiG count, the launcher exits 4, including for an unrecognized log format. Preserve the log and inspect counts and reference identities even after exit 0.

**The run finished but `BIGSCAPE_EXIT` is not 0.**
The launcher then exits 5. Read `<out>/run.log`. The launcher prints the first five `Traceback` or `Error` lines. A crash at the tree step can leave family rows with no `newick` trees. The figure reader refuses a family without a stored tree.

A filled family table does not show that clustering and membership checks finished. Treat the failed run as incomplete until you have checked exactly what finished, and the counts.

**It is much slower than expected.**
Runtime depends on the admitted records, settings, installed version and resources; large runs can take hours. Treat that as a planning example, not a timing guarantee. Start with one core and log the start and end times. The launcher has no memory or time watcher, so do not run jobs at the same time unless their combined budget is approved.

**Path with spaces.**
Keep every path free of spaces. `python mamey_run.py bigscape` stages into a space-free folder for this reason (its `--work-dir` option).

## The database

**"Many records have no family."**
This can be correct. `tools/bigscape_family_verdicts.py` counts a region as a singleton when it has no `bgc_record_family` row at that cutoff, so `singleton_records` is regions minus regions with a row. The `.placement.tsv` output of `tools/bigscape_family_verdicts.py` gives counts per cutoff. Its `region_records` denominator includes all region records in the database, while `records_with_family_row` can be scoped to a selected run; their difference is not automatically the number of singleton inputs admitted to that run. Bind the run's input roster and producer receipt before interpreting absence.
Say "private among placed records" and give both numbers. Never compute a private rate against the total
`bgc_record` count. That table also holds protoclusters and candidate clusters; use `record_type = 'region'`.

**Family ids differ between two runs of the same input.**
Family ids can differ. They are local to one database and run. Join on the source run ID, the cutoff and the complete locus identity. Never use local family IDs or the FAM labels on a figure as identity across runs.

**A widget or figure stops with `RUN_AMBIGUOUS`, `RUN_NOT_IN_DB` or `RUN_UNFINISHED`.**
One database can hold several BiG-SCAPE runs, and each run writes its own family rows. The cohort matrix and clinker pages made by `python mamey_run.py bigscape`, `tools/bigscape_clinker_html.py` and `tools/bigscape_family_figures.py` read one run.
`RUN_AMBIGUOUS` means more than one finished run is present: pass `--run-id` with the run you
reviewed. `RUN_NOT_IN_DB` means that run has no families here. `RUN_UNFINISHED` means the run has no
`end_time`: its process may still be active, or it may have stopped. The recorded families are not a finished result. Check the specific process or job handle and log; if liveness is unknown, keep it unresolved. Preserve partial outputs, then use a separately authorized fresh run only after the prior process has stopped, or choose a reviewed finished run. These diagnostics depend on schema and recorded metadata: without a `run.end_time` column, this selector does not mark runs unfinished. Missing completion metadata or absence of `RUN_UNFINISHED` is not proof of success.

**The same accession appears under two layers.**
The staging copied one genome into two layers. An example is a type strain that is also in a second reference set
under a different assembly. Check the staging manifest by sha256 before the run. If you miss it, the family verdicts
will over-count the reference presence for that genome.

**A strain's second assembly was staged too.**
Two antiSMASH runs of one strain, such as a re-assembly and a cleaned assembly, double the strain's records. They also put near-identical
regions into the same families. Keep one assembly of record per strain in the input. Move the other outside the staged
folder and record it.

## Layers and labels

The figure tool in this section is `tools/render_gcf_synteny_tree.py`. `tools/bigscape_family_figures.py`, the walkthrough command, calls it. Use `--focus` on the batch tool and `--focal` on the single-family tool.

**Reference rows show `[alias unbound: identity hold]`.**
The figure tool labels reference rows from files named `SID_…`, `TYPE_…` or `<stem>__<region>` (reference layers staged beside your queries) by layer, organism and accession. If a reference layer uses another
prefix, pass `--reference-prefix <PREFIX>_` (figure tool) or `--layer-prefix` (verdicts, clinker).

**A query row shows an identity hold although the strain has a package.**
Read the `identity_hold` column of the figure's `<out>_rows.tsv` first. It gives the reason:
`no bound package record for this region file`, `bound package record has no BGC_ID`, `... no Contig`,
`... no antiSMASH_Region`, `contig mismatch: package X vs file Y`, `region mismatch: package X vs file Y`,
or `duplicate Source_GBK key with conflicting records in <files>`. A row binds only when both contig and
region match. Two inventory rows that bind one `Source_GBK` basename differently hold the row. A missing
`--identity` inventory gives the first reason, which is not evidence of a different run. A contig or region
mismatch can come from a different antiSMASH run, such as another strictness profile or assembly; compare the
strictness in `STRICTNESS_MANIFEST.tsv` with the package's antiSMASH run, and check the package's `Source_GBK`
column. Do not invent an alias. Either re-stage from the package's run, or leave the hold and say why.

**Organism on a reference label is `.`**
Web-run antiSMASH GBKs carry `ORGANISM .`, and the organism is on the DEFINITION line. The tool reads it from
there.

**A "private" family with two members of one strain.**
Two region records assigned to one genome cluster together; paralogy, fragmentation or duplicate staging remain hypotheses requiring independent evidence. The verdicts table flags it in
`cross_strain`. Do not report it as cross-strain recurrence.

## Figures

**Row labels are cut off at the left edge.**
The label wraps onto two lines and the figure widens to fit the longest
label. Re-render with the current tool.

**A family of 100+ members renders a figure taller than a page.**
Use `render_gcf_synteny_tree.py --max-tips 40 --focal <strain>` as a display target. It is not a hard ceiling, because every query and MIBiG member is kept. The reference members nearest the focal
rows fill the rest, and the title carries `[pruned view: k of N members]`. The full membership stays in the verdicts
table. A pruned figure never changes a count.

**Rendering one family takes many minutes.**
The homology links are BLOSUM62 global alignments between every gene pair of neighboring rows. Long PKS and NRPS genes make each alignment slow, and a 40-row family has thousands of pairs. Use the Pfam and length prefilter
(`--prefilter-db <bigscape.db>`). When you give `--db`, the prefilter is on by default and uses that database; `--prefilter-db none` turns it off.
The prefilter aligns only pairs whose length ratio allows the identity threshold and that share a Pfam
domain in the BiG-SCAPE scan, or that both lack one. It picks candidate pairs. Do not claim it matches every unfiltered link without checking the result. The caption states the candidate
count.

**The clinker PDF splits a tall page across many sheets.**
Print through `tools/bigscape_clinker_html.py --chrome <binary>`. It adds a `@page` size computed from the track count,
so each family fits on one sheet. Actual pagination also depends on browser and print settings; inspect the saved PDF rather than assuming one sheet or a split.

**Headless Chrome prints a blank page.**
Give it time to run the page script. The tool passes `--virtual-time-budget=4000`. If the PDF is blank on a very tall page, use the HTML.

## Claims

- **"This family is novel."** No. It is private to this panel at this cutoff. Before you use the word candidate, you need genus-matched comparators, a low-identity ClusterBlast result (ClusterBlast compares a region with known clusters) and a gene-level read of the region. A person makes that call.
- **"MIBiG member, so it makes compound X."** No. Family assignment is a similarity grouping under the selected algorithm, input panel, run and cutoff; it does not establish a complete shared pathway or product.
- **"Singleton, so rare."** No. At a cutoff of 0.3 many regions can be singletons, so singleton status says little. Count them from your own placement file.
