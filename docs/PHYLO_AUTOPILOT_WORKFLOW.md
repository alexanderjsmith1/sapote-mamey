# Route 16S queries and prepare placement

Classify your sequence files, route 16S queries against references and
prepare one placement group. You need FASTA files, a local 16S database, and
BLAST+'s `blastn` and `blastdbcmd` available on your terminal's PATH.
Use an existing 16S FASTA or the 16S records from [Barrnap](BARRNAP.md).

## Check the files

```bash
python mamey_run.py phylo-autopilot plan inputs/EXAMPLE-sequences
```

`python mamey_run.py phylo-autopilot` passes its arguments to `tools/phylo_autopilot.py`, so the two forms are the same. The rest of this page uses the front door.

The command prints JSON that lists the files under each label, for example `{"rrna": ["inputs/EXAMPLE-sequences/a.fasta"]}`. It searches the folder and its subfolders. Only files ending `.fa`, `.fasta`, `.fna`, `.faa` or `.fas` (any case) are classified. Every other file is listed under `not_classified_suffix`. A folder that does not exist exits 2 with a message. Compare the JSON with your own file list before you go on.

The labels use size and alphabet only:

- `empty`: the file has no FASTA record;
- `empty_record`: at least one record has a header but no sequence. Fix or remove that record;
- `protein`: an amino-acid-only letter (E, F, I, L, P, Q or Z) is in the first five records;
- `genome`: a record of at least 10,000 letters, or at least 500,000 in total;
- `rrna`: every record is 5,000 letters or shorter.

`rrna` means short sequence, not a checked marker: the tool does not look for 16S. Many short
records that add up to 500,000 letters are labeled `genome`. Run query QC before you use any file.

## Route 16S queries

Use your installed database's absolute prefix; see [local setup](LOCAL_16S_DATABASE.md).
Replace `/tmp/EXAMPLE-reference/16S` below with that prefix. If the shared local database is already set up, you can leave `--db` out.

```bash
python mamey_run.py phylo-autopilot route --query inputs/EXAMPLE-16S.fasta \
  --db /tmp/EXAMPLE-reference/16S
```

Open `routing_table.tsv` in the working folder. It lists matched query IDs,
genus, alignment length, identity, alternatives and route group. `pident` uses
unambiguous columns; `pident_raw` is BLAST's value. Resolve `GENUS_CONFLICT` and
compare query IDs with your FASTA before preparing placement.

## Prepare one group

Choose `--group` from the routing table; this example uses `rare_genera`.
Use a new output directory:

```bash
python mamey_run.py phylo-autopilot run-16s --query inputs/EXAMPLE-16S.fasta \
  --db /tmp/EXAMPLE-reference/16S --group rare_genera \
  --outdir reviews/EXAMPLE-placement --dry-run
```

`--dry-run` runs local BLAST and writes files, then stops before placement.
Open `query_qc.tsv`, `routing_table.tsv`, the group query/reference FASTAs and
`rare_genera_reference.fasta.acc` in that output directory.

The defaults select up to 30 references per query genus, add Streptomyces and
Nocardia comparators, and add Corynebacterium as the outgroup. This route builds its own reference set. It does
not apply the outgroup registry described in
[outgroup and reference sets](OUTGROUP_AND_REFSET_WORKFLOW.md), so the outgroup can differ from
the one that page gives. Review the selected accessions, outgroup and type-material evidence
before approving a tree.

A real run needs the EPA-ng toolchain and `--approved-by`. Give the name of the person who
authorized the tree; the run records it in its receipt. The flag is required unless you use
`--dry-run`. Success is a finished placement folder with a grafted tree and `query_qc.tsv`.
Keep the complete inference panel when a later figure displays fewer tips.
Use [R figure workflows](R_FIGURE_WORKFLOWS.md) for display.

For whole-genome trees, follow [GToTree](GTOTREE_WORKFLOW.md). Its governed v2
route needs the runtime bindings in the [run contract](COMPANION_RUN_CONTRACTS.md);
the shorter `phylo-run` front door omits those controls.
