# Multi-cohort comparison toolkit

These scripts re-draw tables, widgets and print-ready PDFs from packages you have
already made with `run`. Most only re-draw or re-tabulate. A few compute:
`bigscape_run` (BiG-SCAPE), `clade_ani` (all-vs-all ANI), `clade_decontam`
(blastn binning) and `clade_deepdive` (runs the others). These are heavy.
Run them one at a time, and see [companion files](../docs/COMPANION_FILES.md)
for their size limits. `extract_cohort_clusterblast` and `extract_comprehensive_both`
parse results into new tables. Use the
`mamey_run.py` commands first. Come here when a command does not cover the view
you need.

`deliverable_tools/cohort_tools.py` is the one entry point. It lists the scripts and
starts one. The scripts need the Mamey modules and your Python environment
([first run](../docs/reader/01_FIRST_RUN.md)). Some also need Pandoc or the BiG-SCAPE
environment ([companion files](../docs/COMPANION_FILES.md)).

## Find a tool

From the program folder, with your environment active:

```bash
python deliverable_tools/cohort_tools.py list
python deliverable_tools/cohort_tools.py doctor
```

`list` prints the title `Sapote-Mamey Multi-Cohort Comparison Toolkit` and a count of
tools, grouped by theme, with a one-line description each. A script with no
description says `inspect source before dispatch`. Names that start with `_` are
helpers, not tools.

`doctor` prints one row per helper program (Python, Pandoc, GToTree, IQ-TREE,
fastANI, BLASTp, BiG-SCAPE). The status can be `PATH`, `PROJECT`, `PROJECT*` or `MISSING`. PATH lookup and project-file existence are different checks; neither establishes working execution, and `PROJECT*` is not a passing runtime test. `MISSING` for a
program you do not use is fine.

`doctor` looks for programs under the folder in `SAPOTE_ROOT` (default
`~/sapote_workspace`). The scripts themselves read `SAPOTE_WORKSPACE_ROOT` (default:
the folder you run them from). Set whichever your tool needs.

## Run one tool

Pass the tool name and its arguments:

```bash
python deliverable_tools/cohort_tools.py assembly_line_pdf \
  --strain EXAMPLE --runs-root runs --out runs/EXAMPLE/post_seal/assembly_lines
```

`--runs-root` is a folder that holds the finished package. The tool writes
`EXAMPLE_assembly_lines.pdf` into `--out`. A line starting `[SKIP]` means it wrote no PDF.
There are two skips. One says no `antismash_modules.csv` was found under `--runs-root`; the
package may still exist, so check the path and the module table. The other says the module
table has no NRPS/PKS assembly-line domain rows; it reports the module table only, so inspect
the table before you conclude why. Open the PDF and check the pages before you share it.

Each tool has its own arguments. Run `python deliverable_tools/<tool>.py -h` first.
The launcher forwards arguments as they are and adds no dry run. A shell tool
(`.sh`) can act before it prints help, so read it before you run it.

Write into a new output folder. Do not write into a package you want to keep
unchanged ([post-seal write rules](../docs/POSTSEAL_READERS.md)).

## Tools that change files in place

| Tool | What it reads | What it writes |
|---|---|---|
| `enrich_swissprot` | Swiss-Prot result CSVs and `sapote_deliverables/roster_v2/<strain>_roster_v2.json` | The roster, in place. It does not run BLASTp. |
| `backfill_coords_from_antismash` | The antiSMASH JSON inside the input archive | Coordinates and ClusterBlast values added to a roster |
| `build_strain_dossier` | Roster JSON, novelty board, comparison CSV | A Markdown dossier, and a Word file if Pandoc and python-docx are present. Each file goes to both `strain_data/<strain>/` and `dossiers/` under `SAPOTE_WORKSPACE_ROOT`. A missing converter still exits normally after writing Markdown, so check the formats. |

`enrich_swissprot` joins on the (BGC, gene) pair. It holds a key that has two rank-1
Swiss-Prot rows (`DUPLICATE_SWISSPROT_RANK1_KEY`) or that repeats in the roster
(`DUPLICATE_ROSTER_GENE_KEY`), and lists each under `join_holds.swissprot` in the roster.
`backfill_coords_from_antismash` joins on the locus tag alone. It holds a tag that appears
on two CDS features in the antiSMASH JSON and lists it under `join_holds.antismash_coords`
(`DUPLICATE_ANTISMASH_LOCUS_TAG`). Both print the held count on their console line. A blank
`hit_rank` counts as rank 1. Keep every roster and source row; resolve a held key with the
full locus context instead of deleting rows. Both tools still rewrite the roster in place, so
copy the roster folder first and run the tool on the copy. If a tool fails partway, compare
the copy with your original before you retry.

Bind the chosen archive to the target run by source path and SHA-256: the first discovered
qualifying archive is not independently matched to a recorded input digest. Verify the full
strain / contig / region / BGC alias and gene identities; a unique locus tag alone does not
prove source binding. Compare the resulting hold list with this run's console count. A clean
rerun does not clear earlier holds: each tool writes its `join_holds` entry only when it finds
duplicates, so a list from an earlier run stays in the roster.

`_batch_enrich.sh` and `_build_all.sh` are old batch scripts with fixed paths. Do not
use them.

## Rules for every tool

- A capacity class, a similarity or a count of strains with a feature does not show
  that a compound is made, that it is active or that it is new.
- Name each cluster as `strain / full node-or-contig / region / BGC alias`.
- Some tools read the exclusion list through `mamey.exclusions`. If binding it fails
  they can warn and carry on with an empty list. Fix the binding
  ([cohort pack](../docs/COHORT_PACK_INTERFACE.md)); do not accept the empty list.
- `TOOLS_INDEX.md` is written by `cohort_tools.py index`. Run that only if you
  mean to replace the file.
