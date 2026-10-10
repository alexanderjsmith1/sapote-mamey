# BiG-SCAPE troubleshooting

Symptoms first, then the cause and the fix. Every entry here happened at least once on a real cohort run.
Walkthrough: [cohort walkthrough](../BIGSCAPE_COHORT_WALKTHROUGH.md). Rules: [cohort workflow](../BIGSCAPE_GCF_WORKFLOW.md). For exact reader selection, skipped/failed outputs and recovery receipts, read [BiG-SCAPE reader recovery](../../tools/BIGSCAPE_READER_RECOVERY.md).

## Launcher preflight and writes

The launcher requires `BIGSCAPE_ENV_BIN` and `PFAM_HMM`; it does not create or install that environment. Pass an explicit resource choice such as `--cores 1`: the shipped shell launcher defaults to four cores, while the cohort SOP recommends one unless more are approved. Read the selected input/output paths before execution.

`--mibig-dir` changes a symlink inside the installed BiG-SCAPE package (`MIBiG/mibig_antismash_<name>_gbk`) before checking the reference count. This mutates the dependency environment as well as writing run outputs. A rejected reference-count check can leave the new symlink in place. Use an authorized writable environment and record the previous target if recovery is required; do not assume a failed launch made no changes. The launcher checks for at least 2,000 reference GBKs, so a deliberately small custom panel will be refused by this wrapper even if another workflow could use it.

The launcher explicitly checks the HMM file and its `.h3i` companion. Independently verify all pressed-library companions, asset hashes and versions; that limited filename check alone is not full Pfam consistency validation.

## The run

**`FileNotFoundError: fasttree` (or hmmsearch, diamond) after hours of clustering.**
The bigscape binary was called by absolute path without the env on PATH; its subprocess tools are looked up by bare
name at the per-family tree step, which runs after clustering. The database can be incomplete. Preserve the log and database before deciding whether a governed recovery is possible.
Fix: run through `tools/bigscape_launch.sh` (it exports the env bin onto PATH and refuses to start without
`fasttree`). If you must call bigscape directly, `export PATH=<env>/bin:$PATH` first.

**`Loading 0 mibig GBKs` although you asked for MIBiG.**
BiG-SCAPE loads MIBiG only through `-m <name>`, from a folder inside the installed package
(`big_scape/MIBiG/mibig_antismash_<name>_gbk`). If that folder is a dead symlink, the loader says "already present"
by folder name and loads nothing, silently. Passing the MIBiG folder with `-i` or `-r` also loads nothing: those
paths filter file names to "region"/"cluster" and every `BGC*.gbk` is dropped.
Fix: `--mibig-dir <folder> --mibig-name <name>` on the launcher, which relinks the slot and refuses to run unless
the link resolves to at least 2,000 files. Read the loaded counts at the end of every run.

**The run ran but `BIGSCAPE_EXIT` is not 0.**
Read `<out>/run.log`; the launcher prints the first `Traceback`/`Error` lines. A tree-step crash can leave family rows but absent `newick` trees. The figure reader refuses a family without a stored tree. A populated family table is not sufficient evidence that clustering and membership QA completed; retain the failed run as incomplete until exact completed scope and counts are verified.

**It is much slower than expected.**
Cores above 4 do not help on a laptop and starve everything else. 18,000 records took about 3 hours at 4 cores;
the earlier estimate of 6 to 20 hours was wrong on the safe side. Do not run two BiG-SCAPE jobs at once.

**Path with spaces.**
BiG-SCAPE and the Pfam path tolerate spaces, but stage inputs in a space-free folder anyway; several downstream shell
tools do not.

## The database

**"Only half the records have a family."**
Correct and expected. BiG-SCAPE 2 writes `bgc_record_family` rows only for records inside a connected component at
that cutoff; singletons get no row. `bigscape_family_verdicts.py … .placement.tsv` gives the denominator per cutoff.
Say "private among placed records" and give both numbers. Never compute a private rate against the total
`bgc_record` count (that table also holds protoclusters and candidate clusters; use `record_type = 'region'`).

**Family ids differ between two runs of the same input.**
Family ids can differ and are local to a database/run. Use the governed join including source run ID, cutoff and complete locus binding; never rely on local family IDs or visual FAM labels as portable identity.

**The same accession appears under two layers.**
The staging copied one genome into two layers (for example a type strain that is also in a second reference set
under a different assembly). Check the staging manifest by sha256 before the run; after the run, the family verdicts
will over-count the reference presence for that genome.

**A strain's second assembly was staged too.**
Two antiSMASH runs of one strain (a re-assembly, a cleaned assembly) double the strain's records and put near-identical
regions into the same families. Keep one assembly of record per strain in the input; park the other outside the staged
folder and record it.

## Layers and labels

**Reference rows show `[alias unbound: identity hold]`.**
The sealed figure tool (v9.7.432) only knew `<strain>_<NODE…>.regionNNN` and MIBiG names; the v9.7.433 tool labels
`SID_…`, `TYPE_…` and `<stem>__<region>` files by layer, organism and accession. If a reference layer uses another
prefix, pass `--reference-prefix <PREFIX>_` (figure tool) or `--layer-prefix` (verdicts, clinker).

**A query row shows an identity hold although the strain has a package.**
The staged GBK and the package inventory come from different antiSMASH runs (loose versus relaxed, or a different
assembly), so contig names or region numbers differ. Check `_ANTISMASH_CANONICAL/loose/` versus `relaxed/` and the
package's `Source_GBK` column. Do not invent an alias; either re-stage from the package's run or leave the hold and
say why.

**Organism on a reference label is `.`**
Web-run antiSMASH GBKs carry `ORGANISM .`; the organism is on the DEFINITION line. The v9.7.433 tool reads it from
there; older outputs need the fix.

**A "private" family with two members of one strain.**
Two regions of one genome cluster together (paralogous loci or a split region). The verdicts table flags it in
`cross_strain`; do not report it as cross-strain recurrence.

## Figures

**Row labels are cut off at the left edge.**
v9.7.432 used a fixed label strip; v9.7.433 wraps the label onto two lines and widens the figure to the longest
label. Re-render with the current tool.

**A family of 100+ members renders a figure taller than a page.**
Use `--max-tips 40 --focal <strain>` as a display target: it is not a hard ceiling because every query and MIBiG member is kept, the reference members nearest the focal
rows fill the rest, and the title carries `[pruned view: k of N members]`. The full membership stays in the verdicts
table; a pruned figure never changes a count.

**Rendering one family takes many minutes.**
The homology links are BLOSUM62 global alignments between every gene pair of neighbouring rows; PKS/NRPS genes of
2,000 to 5,000 aa cost 0.1 s per pair and a 40-row family has thousands of pairs. Use the Pfam/length prefilter
(`--prefilter-db <bigscape.db>`): only pairs whose length ratio allows the identity threshold and that share a Pfam
domain in the BiG-SCAPE scan, or both lack one, are aligned. The filter selects candidate pairs; do not claim equivalence to all unfiltered links without checking the result. The caption states the candidate
count.

**The clinker PDF splits a tall page across many sheets.**
Print through `bigscape_clinker_html.py --chrome <binary>`: it injects a `@page` size computed from the track count
so each family is one sheet. Browser "print to PDF" from the open HTML will paginate.

**Headless Chrome prints a blank page.**
Give it time to run the page script: the tool passes `--virtual-time-budget=4000`. A page with more than about 150
tracks may need the HTML instead.

## Claims

**"This family is novel."** No. It is private to this panel at this cutoff. Genus-matched comparators, low-identity
ClusterBlast and the gene-level read of the region are all required before the word candidate, and the ruling is a
person's. **"MIBiG member, so it makes compound X."** No. Same family means similar architecture. **"Singleton, so
rare."** No. At 0.3 most records are singletons; the base rate makes singleton status uninformative.
