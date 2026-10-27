# BiG-SCAPE troubleshooting

Symptoms first, then the cause and the fix. Every entry here happened at least once on a real cohort run.
Walkthrough: [cohort walkthrough](../BIGSCAPE_COHORT_WALKTHROUGH.md). Rules: [cohort workflow](../BIGSCAPE_GCF_WORKFLOW.md). For exact reader selection, skipped or failed outputs and recovery receipts, read [BiG-SCAPE reader recovery](../../tools/BIGSCAPE_READER_RECOVERY.md).

## Launcher preflight and writes

The launcher, `tools/bigscape_launch.sh`, needs `BIGSCAPE_ENV_BIN` and `PFAM_HMM` set. It does not create or install that environment. Pass an explicit resource choice such as `--cores 1`. The launcher defaults to four cores, but the cohort SOP recommends one unless more are approved. Read the input and output paths before you run it.

`--mibig-dir` changes a symlink inside the installed BiG-SCAPE package (`MIBiG/mibig_antismash_<name>_gbk`). It does this before it checks the reference count. So it changes the dependency environment as well as writing run outputs. If the count check then fails (exit 3), the new symlink stays in place. Use a writable environment you are allowed to change. Record the previous link target if you may need to restore it. Do not assume a failed launch changed nothing.

With `--mibig-dir`, the MIBiG folder must hold at least 2,000 GBKs; the launcher refuses a smaller MIBiG panel with exit 3. Other reference inputs are not counted.

The launcher checks only the HMM file and its `.h3i` companion. Check all the pressed-library companions, asset hashes and versions yourself. That filename check is not a full Pfam consistency check.

Use a fresh run-output folder. The launcher creates or reuses its positional `out_dir` and overwrites `<out>/run.log`. It names the database `<out>/<label>.db`. The default label is `run_<today's date>`, so a second run on the same day into the same folder points at the same database file. Nothing guards against reusing a folder or overwriting earlier evidence. A later failure can leave partial outputs and an overwritten old log.

Keep previous attempts. Record the actual command, exit status, input, tool and database hashes, and the complete log separately. The version and count lines the launcher prints are not a completion receipt.

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
The recorded incident took about 3 hours for 18,000 records at four cores. That is one observation, not a controlled scaling study or a runtime promise for other hardware. Do not assume that more cores always help, or never help. Record the actual panel, environment, resource setting and approval.

The interactive cohort policy starts with one core. The launcher defaults to four and has no memory or time watcher for the whole job. Avoid running jobs at the same time unless their combined budget is approved.

**Path with spaces.**
BiG-SCAPE and the Pfam path tolerate spaces. Stage inputs in a folder without spaces anyway, because several downstream shell
tools do not.

## The database

**"Only half the records have a family."**
This is correct and expected. BiG-SCAPE 2 writes `bgc_record_family` rows only for records inside a connected component at
that cutoff. Singletons get no row. The `.placement.tsv` output of `tools/bigscape_family_verdicts.py` gives the denominator per cutoff.
Say "private among placed records" and give both numbers. Never compute a private rate against the total
`bgc_record` count. That table also holds protoclusters and candidate clusters; use `record_type = 'region'`.

**Family ids differ between two runs of the same input.**
Family ids can differ. They are local to one database and run. Join on the source run ID, the cutoff and the complete locus identity. Never use local family IDs or the FAM labels on a figure as identity across runs.

**The same accession appears under two layers.**
The staging copied one genome into two layers. An example is a type strain that is also in a second reference set
under a different assembly. Check the staging manifest by sha256 before the run. If you miss it, the family verdicts
will over-count the reference presence for that genome.

**A strain's second assembly was staged too.**
Two antiSMASH runs of one strain, such as a re-assembly and a cleaned assembly, double the strain's records. They also put near-identical
regions into the same families. Keep one assembly of record per strain in the input. Move the other outside the staged
folder and record it.

## Layers and labels

The figure tool in this section is `tools/render_gcf_synteny_tree.py`.

**Reference rows show `[alias unbound: identity hold]`.**
The figure tool up to v9.7.432 only knew `<strain>_<NODE…>.regionNNN` and MIBiG names. From v9.7.433 it labels
`SID_…`, `TYPE_…` and `<stem>__<region>` files by layer, organism and accession. If a reference layer uses another
prefix, pass `--reference-prefix <PREFIX>_` (figure tool) or `--layer-prefix` (verdicts, clinker).

**A query row shows an identity hold although the strain has a package.**
The staged GBK and the package inventory come from different antiSMASH runs, for example loose versus relaxed, or a different
assembly. So the contig names or region numbers differ. Check `_ANTISMASH_CANONICAL/loose/` versus `relaxed/` and the
package's `Source_GBK` column. Do not invent an alias. Either re-stage from the package's run, or leave the hold and
say why.

**Organism on a reference label is `.`**
Web-run antiSMASH GBKs carry `ORGANISM .`, and the organism is on the DEFINITION line. From v9.7.433 the tool reads it from
there. Outputs drawn by older versions need a re-render.

**A "private" family with two members of one strain.**
Two regions of one genome cluster together (paralogous loci or a split region). The verdicts table flags it in
`cross_strain`. Do not report it as cross-strain recurrence.

## Figures

**Row labels are cut off at the left edge.**
v9.7.432 used a fixed label strip. From v9.7.433 the label wraps onto two lines and the figure widens to fit the longest
label. Re-render with the current tool.

**A family of 100+ members renders a figure taller than a page.**
Use `--max-tips 40 --focal <strain>` as a display target. It is not a hard ceiling, because every query and MIBiG member is kept. The reference members nearest the focal
rows fill the rest, and the title carries `[pruned view: k of N members]`. The full membership stays in the verdicts
table. A pruned figure never changes a count.

**Rendering one family takes many minutes.**
The homology links are BLOSUM62 global alignments between every gene pair of neighboring rows. PKS and NRPS genes of
2,000 to 5,000 aa cost 0.1 s per pair, and a 40-row family has thousands of pairs. Use the Pfam and length prefilter
(`--prefilter-db <bigscape.db>`). When you give `--db`, the prefilter is on by default and uses that database; `--prefilter-db none` turns it off.
The prefilter aligns only pairs whose length ratio allows the identity threshold and that share a Pfam
domain in the BiG-SCAPE scan, or that both lack one. It picks candidate pairs. Do not claim it matches every unfiltered link without checking the result. The caption states the candidate
count.

**The clinker PDF splits a tall page across many sheets.**
Print through `tools/bigscape_clinker_html.py --chrome <binary>`. It adds a `@page` size computed from the track count,
so each family fits on one sheet. A browser "print to PDF" from the open HTML will split it into pages.

**Headless Chrome prints a blank page.**
Give it time to run the page script. The tool passes `--virtual-time-budget=4000`. A page with more than about 150
tracks may need the HTML instead.

## Claims

**"This family is novel."** No. It is private to this panel at this cutoff. Genus-matched comparators, low-identity
ClusterBlast and the gene-level read of the region are all required before the word candidate, and the ruling is a
person's. **"MIBiG member, so it makes compound X."** No. Same family means similar architecture. **"Singleton, so
rare."** No. At 0.3 most records are singletons; the base rate makes singleton status uninformative.
