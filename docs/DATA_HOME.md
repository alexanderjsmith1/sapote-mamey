# Start a Strain Master and submit a file

Keep recorded copies of project files with their source paths and SHA-256 values.
You need the installed program, a new master folder and an existing result file.
For an index that leaves all files in place, use [Project file index](PROJECT_DATA_HOME.md).

## Create the master

Run this from the program folder:

```bash
python mamey_run.py strain-master init --master ../EXAMPLE-master
```

`--master` chooses the storage root. The command creates its layout, area READMEs,
settings, changelog and inbox ledger. Keep working analyses outside the master;
submit finished files through its inbox.

<a id="the-one-way-in"></a>

## Submit one result for review

This example submits the region inventory from the first-run package:

```bash
python mamey_run.py strain-master submit --master ../EXAMPLE-master \
  --chat submitter --topic 'EXAMPLE inventory' --target '04 Gene clusters/Source tables' \
  --summary 'Region inventory for EXAMPLE' --check 'Recount rows from the saved inventory' \
  runs/EXAMPLE/package/AS-40_2_inventory.csv
```

Choose your own identifier for `--chat`. The topic names the submission, the target
chooses its destination, and the summary/check tell the reviewer what to reproduce.
The source stays in place; a byte copy is staged in `00 Inbox`. Save the printed
submission ID.

```bash
python mamey_run.py strain-master status --master ../EXAMPLE-master
python mamey_run.py strain-master check --master ../EXAMPLE-master
```

Expect `SUBMITTED` until review. The check prints `RESULT: PASS`, `PASS with warnings`
or `FAIL`; read the individual findings. A staged file is not yet a registered result.

## Review, then apply

A different reviewer checks hashes, counts, complete locus identities, existing
records, destination and claims before accepting the submission. They use their
own `--chat` identifier; changing identifiers alone is not independent review.
Only an accepted submission can be applied to its destination.

The [storage reference](reference/STRAIN_MASTER_STORAGE_REFERENCE.md#the-one-way-in)
gives verify/apply commands, return handling and the full checklist. It also covers
record edits, folder imports, hard links, replacement backups, layouts and settings.
Use the same submission ID throughout; do not write directly into an area folder.

<a id="where-mamey-outputs-land"></a>

## Find existing files

For an existing master, inspect its area README and `LAYOUT.md`, or run:

```bash
python mamey_run.py strain-master where --master ../EXAMPLE-master \
  --type '04 Gene clusters/Source tables' --strain EXAMPLE
```

The result lists recorded matches and may locate unregistered/raw-store files;
choose and bind the actual source before analysis. The reference explains
[output kinds](reference/STRAIN_MASTER_STORAGE_REFERENCE.md#where-mamey-outputs-land)
and how the master resolves assemblies and flavored antiSMASH results.
