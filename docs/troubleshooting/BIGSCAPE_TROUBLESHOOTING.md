# BiG-SCAPE troubleshooting

Symptoms first, then the cause and the fix.
Walkthrough: [cohort walkthrough](../BIGSCAPE_COHORT_WALKTHROUGH.md). Rules: [cohort workflow](../BIGSCAPE_GCF_WORKFLOW.md). For exact reader selection, skipped or failed outputs and recovery receipts, read [BiG-SCAPE reader recovery](../../tools/BIGSCAPE_READER_RECOVERY.md).

## Launcher preflight and writes

The launcher is `tools/bigscape_launch.sh`. It does not create or install the BiG-SCAPE environment. Before each run:

1. Set `BIGSCAPE_ENV_BIN` (the environment's `bin` folder) and `PFAM_HMM` (the pressed `Pfam-A.hmm`).
2. Use a fresh output folder. The launcher overwrites `<out>/run.log`. It names the database `<out>/<label>.db`, and the default label is `run_<today's date>`. A second run on the same day in the same folder points at the same database file.
3. Pass `--cores 1`. The launcher defaults to four cores. The walkthrough starts with one.
4. Check the Pfam companions yourself. The launcher checks only the `.h3i` file, not `.h3f`, `.h3m` or `.h3p`.
5. Keep the command, the exit status, the complete log, and the input, tool and database hashes. The version and count lines the launcher prints are not a completion receipt.
6. With `--mibig-dir`, record the previous link target first (see below).

`--mibig-dir` changes a symlink inside the installed BiG-SCAPE package (`MIBiG/mibig_antismash_<name>_gbk`). It does this before it checks the reference count. If the check then fails (exit 3), the new link stays. Use an environment you may change.

`--mibig-name` is a label you choose, for example `local2088`. The `--mibig-dir` folder must hold the MIBiG `BGC*.gbk` files, at least 2,000 of them. The launcher refuses a smaller panel with exit 3. Other reference inputs are not counted.

Launcher exit codes:

| Code | Meaning |
|---|---|
| 0 | BiG-SCAPE exited 0 (and, with `--mibig-dir`, the log proved a positive MIBiG count). |
| 2 | Setup error: `bigscape` not executable, Pfam not pressed, `fasttree` missing, an unknown argument, a missing input folder, no GBKs in it, or `--mibig-dir` without `--mibig-name`. |
| 3 | The MIBiG folder holds fewer than 2,000 GBKs. |
| 4 | `--mibig-dir` was given but the log did not show a positive loaded MIBiG count. |
| other | BiG-SCAPE's own exit code. Read `<out>/run.log`. |

## The run

**`FileNotFoundError: fasttree` (or hmmsearch, diamond) after hours of clustering.**
The bigscape binary was called by absolute path without the environment on PATH. Its helper tools are looked up by bare
name at the per-family tree step, which runs after clustering. The database can be incomplete. Keep the log and the database before you decide whether a recovery is possible.
Fix: run through `tools/bigscape_launch.sh`. It puts the environment's bin folder on PATH and refuses to start without
`fasttree`. If you must call bigscape directly, run `export PATH=<env>/bin:$PATH` first.

**`Loading 0 mibig GBKs` although you asked for MIBiG.**
BiG-SCAPE loads MIBiG only through `-m <name>`, from a folder inside the installed package
(`big_scape/MIBiG/mibig_antismash_<name>_gbk`). If that folder is a dead symlink, the loader says "already present"
because the folder name exists, and silently loads nothing. Passing the MIBiG folder with `-i` or `-r` also loads nothing. Those
options keep only file names containing "region" or "cluster", so every `BGC*.gbk` is dropped.
Fix: use `--mibig-dir <folder> --mibig-name <name>` on the launcher. It relinks the slot and refuses to run unless
the link resolves to at least 2,000 files. After a successful run, it exits with 4 if the log does not show a positive MIBiG count. Still read the loaded counts at the end of every run.

**The run finished but `BIGSCAPE_EXIT` is not 0.**
Read `<out>/run.log`. The launcher prints the first five `Traceback` or `Error` lines. A crash at the tree step can leave family rows with no `newick` trees. The figure reader refuses a family without a stored tree.

A filled family table does not show that clustering and membership checks finished. Treat the failed run as incomplete until you have checked exactly what finished, and the counts.

**It is much slower than expected.**
Time grows with the number of records. Expect hours for thousands of regions. Start with one core and log the start and end times. The launcher has no memory or time watcher, so do not run jobs at the same time unless their combined budget is approved.

**Path with spaces.**
Keep every path free of spaces. `python mamey_run.py bigscape` stages into a space-free folder for this reason (its `--work-dir` option).

## The database

**"Many records have no family."**
This can be correct. `tools/bigscape_family_verdicts.py` counts a region as a singleton when it has no `bgc_record_family` row at that cutoff, so `singleton_records` is regions minus regions with a row. The `.placement.tsv` output of `tools/bigscape_family_verdicts.py` gives the denominator per cutoff.
Say "private among placed records" and give both numbers. Never compute a private rate against the total
`bgc_record` count. That table also holds protoclusters and candidate clusters; use `record_type = 'region'`.

**Family ids differ between two runs of the same input.**
Family ids can differ. They are local to one database and run. Join on the source run ID, the cutoff and the complete locus identity. Never use local family IDs or the FAM labels on a figure as identity across runs.

**A widget or figure stops with `RUN_AMBIGUOUS`, `RUN_NOT_IN_DB` or `RUN_UNFINISHED`.**
One database can hold several BiG-SCAPE runs, and each run writes its own family rows. The cohort matrix and clinker pages made by `python mamey_run.py bigscape`, `tools/bigscape_clinker_html.py` and `tools/bigscape_family_figures.py` read one run.
`RUN_AMBIGUOUS` means more than one finished run is present: pass `--run-id` with the run you
reviewed. `RUN_NOT_IN_DB` means that run has no families here. `RUN_UNFINISHED` means the run has no
`end_time`: it was interrupted after writing some families, so its families are not a result. Rerun it,
or choose a finished run.

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
The staged GBK and the package inventory come from different antiSMASH runs, for example a different strictness profile or a different
assembly. So the contig names or region numbers differ. Compare the strictness in `STRICTNESS_MANIFEST.tsv` with the package's antiSMASH run, and check the
package's `Source_GBK` column. Do not invent an alias. Either re-stage from the package's run, or leave the hold and
say why.

**Organism on a reference label is `.`**
Web-run antiSMASH GBKs carry `ORGANISM .`, and the organism is on the DEFINITION line. The tool reads it from
there.

**A "private" family with two members of one strain.**
Two regions of one genome cluster together (paralogous loci or a split region). The verdicts table flags it in
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
so each family fits on one sheet. A browser "print to PDF" from the open HTML will split it into pages.

**Headless Chrome prints a blank page.**
Give it time to run the page script. The tool passes `--virtual-time-budget=4000`. If the PDF is blank on a very tall page, use the HTML.

## Claims

- **"This family is novel."** No. It is private to this panel at this cutoff. Before you use the word candidate, you need genus-matched comparators, a low-identity ClusterBlast result (ClusterBlast compares a region with known clusters) and a gene-level read of the region. A person makes that call.
- **"MIBiG member, so it makes compound X."** No. Same family means similar architecture.
- **"Singleton, so rare."** No. At a cutoff of 0.3 many regions can be singletons, so singleton status says little. Count them from your own placement file.
