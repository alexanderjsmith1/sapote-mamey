# Outgroups and reference sets

Two tools prepare the reference FASTA that [16S placement](PHYLO_PLACEMENT_WORKFLOW.md) needs.

- `tools/outgroup_registry.py` looks up the outgroup for a genus.
- `tools/phylo_refset.py` builds a reference set for your queries, removes duplicate strains and adds the outgroup.

Run `phylo_refset.py` first, then `phylo_place.py build-ref` with its output. The [autopilot route](PHYLO_AUTOPILOT_WORKFLOW.md) builds its own reference set and does not use these tools.

An outgroup is a taxon outside your group of interest. It sets the root of the tree. A governed registry is a table of chosen outgroups that you or your lab have reviewed and selected.

## 1. Set up

Work from the bundle root in the activated environment. You need:

- **A governed registry.** The bundled `mamey/data/outgroup_registry.tsv` is a reference snapshot. The tools refuse it as project authority and stop with `OUTGROUP_AUTHORITY_UNBOUND`. To make your own, copy that file to a folder you control, review every row you will use, and select the copy. Keep the header and these tab-separated columns: `tree_scope`, `ingroup_taxon`, `family`, `outgroup_genus`, `outgroup_species_strain`, `assembly_accession`, `status`, `rationale`. Record the file's SHA-256.
- **A local 16S BLAST database.** See [LOCAL_16S_DATABASE.md](LOCAL_16S_DATABASE.md).
- **BLAST+** on your machine.

Bind them to real paths:

```bash
export OUTGROUP_REGISTRY="/absolute/path/to/your/OUTGROUP_REGISTRY.tsv"
export OUTGROUP_CACHE="/absolute/path/to/writable/outgroup_cache"
export BLAST_BIN="/absolute/path/to/blast/bin"
```

`OUTGROUP_CACHE` must be outside the bundle. The 16S database location comes from the shared lookup described in [LOCAL_16S_DATABASE.md](LOCAL_16S_DATABASE.md#how-the-tools-find-the-blast-database). Check the registry first. A refusal later costs the marker searches you already ran.

## 2. Look up an outgroup

```bash
python tools/outgroup_registry.py list                       # every registered taxon and its outgroup
python tools/outgroup_registry.py lookup Actinomadura        # one row
python tools/outgroup_registry.py get-16s Streptomyces       # the outgroup's 16S FASTA
python tools/outgroup_registry.py genome Nocardia --fetch    # accession and a fetch script
python tools/outgroup_registry.py cache-16s --all            # fill the cache for every row
```

What you get:

- `lookup` prints the registry row: outgroup genus, species and strain, accession and status.
- `get-16s` extracts the outgroup's 16S from your local database and saves it in `OUTGROUP_CACHE/16S/<Genus>_<species>.fasta`. It reuses a cached file whose header passes the 16S admission screen. When the cached file fails the screen, or you pass `--force`, it extracts the record again into a new file and screens that. A new record that fails is deleted and the old cache file is left as it was. A new record that passes replaces the cache, and the old file is kept beside it as `<name>.fasta.replaced-<time>-<pid>`. `--out` must name a file that does not exist yet.
- `genome --fetch` prints the assembly accession and writes a `datasets` fetch script in `OUTGROUP_CACHE/genomes/`. It does not download. If a script of that name already exists with the same text, it is reused. If its text differs, the command stops and leaves it unchanged. Read the script, then run it yourself.
- Add `--scope family` for a family-level tree. The default scope is genus. A genus tree roots on a sister genus. A family tree roots outside the family.

Check the row you get before you use it:

- Read `status` and `tree_scope`. If no row has the scope you asked for, the tool uses the first row for the same taxon at any scope. A family request can return a genus row.
- If two unlocked rows match, the tool uses the first and prints a warning.
- `list` shows rows without the authority check. `cache-16s` exits 0 even when it reports missing entries. Read its output.
- The cache filename comes from the outgroup name, not the registry hash. After you change the registry, clear the cache entry and extract again.
- If the ruled accession is missing from your database, the tool picks a record by genus name. That is not the ruled sequence. Treat it as an open question until you have checked it.

## 3. Build the reference set

```bash
python tools/phylo_refset.py build \
    --query cohort_16S.fasta --group streptomyces \
    --outgroup-genus Streptomyces --out refs_final.fasta
```

`--group` names the cohort. `--outgroup-genus` names the genus whose outgroup you want; with the shipped snapshot, `Streptomyces` returns a *Gordonia* row. It does not add Streptomyces as the outgroup.

The build takes the top five named RefSeq hits per query (`--top`), removes duplicates and adds the registry outgroup. The standalone steps are `marker-blast`, `dedup` and `add-outgroup`. Run `python tools/phylo_refset.py build --help` for `--db`, `--identity` and `--scope`.

Then pass `refs_final.fasta` to `build-ref`. The outgroup is already in it, so you do not need `--add-outgroup`. One exception: if `--group` is a single genus name such as `Actinomadura`, `build-ref` requires `--add-outgroup` with a sister genus.

### How duplicates are removed

Every collapse is written to a report named `<out>_DEDUP_REPORT.tsv`. Use an `--out` that ends in `.fasta`, or the report can overwrite your FASTA.

- **Tier 1, metadata:** the same species and strain token under two RefSeq accessions. One is kept.
- **Tier 2, sequence:** same-species records whose 16S meets `--identity` (default 99.5%) with at least 90% coverage of the shorter sequence. One per group is kept. Tier 2 needs `makeblastdb` and `blastn`. Without them it is skipped with a warning and Tier 1 still runs.
- **Which record stays:** a recognized collection token first (DSM, then ATCC, NBRC, JCM, NRRL), then any strain token, then the longer sequence, then the lower accession.

Removing a duplicate tip does not show that two collection IDs are one physical strain. The ranking does not show type status. For a `[Type]` label, use NCBI Assembly type-material evidence.

### Check the result

- Count your queries, the references retained and the outgroup. `phylo_refset.py` skips a failed or empty extraction, writes fewer records and still exits 0. A build can end up holding only the outgroup.
- The tools do not write a hash receipt or refuse an existing output. Use new paths and save the hashes of your outputs.

## 4. Add an outgroup at the placement step

If you built the set without `phylo_refset.py`, `phylo_place.py build-ref` and `all` accept `--add-outgroup GENUS` to append the registry outgroup. Do not use both routes for the same set.

## What a reference set can claim

16S is an anchor, not a species call. The set gives "nearest among the chosen references". Removing duplicates does not change that. Building the reference tree needs approval, as described in [the placement workflow](PHYLO_PLACEMENT_WORKFLOW.md).
