# Choose an antiSMASH input or a saved package

Choose whether to extract antiSMASH results or read an existing Mamey package.
You need your ZIP and the installed program. Run commands from the folder
containing `mamey_run.py`.

Look inside the ZIP with your file browser. A code ZIP contains `mamey_run.py`;
start with [Install](../INSTALL.md) for that file.

## antiSMASH results

Results contain region GenBank files and may include JSON, HTML and ClusterBlast
folders. Preview an antiSMASH ZIP:

```bash
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
```

Check the reported strain name and input warnings, then follow
[Your first run](../reader/01_FIRST_RUN.md). The preview's region count can miss
supported filename extensions; [input evidence](../ANTISMASH_INPUTS_CONSUMED.md)
explains that limit.

For one public region accession, use [single-region inputs](SOP-07_Single_Region_Public_Accession_Inputs.md).
Keep its accession/version and label its role as a reference, comparison or parser
fixture. A public accession alone does not choose the release setting.

## Saved Mamey package

A Complete_Package ZIP contains `package/manifest.json` and checksums;
`package/OPEN_ME_FIRST.html` is an optional entry page. Run `inspect` on it first. It refuses a ZIP with a
duplicate or unsafe manifest, and it checks every member with the extractor's own
preflight before anything is written. When it passes, it names the strain. Then
extract into a new, unused working folder, because extraction can replace files
there, and validate the result:

```bash
mkdir -p reviews && \
  python mamey_run.py inspect ~/Downloads/EXAMPLE_Complete_Package.zip && \
  mkdir reviews/EXAMPLE-saved && \
  python -m zipfile -e ~/Downloads/EXAMPLE_Complete_Package.zip reviews/EXAMPLE-saved && \
  python mamey_run.py validate reviews/EXAMPLE-saved/package
```

If any command fails, stop and inspect the error. Preserve any partial working folder and choose a
fresh name after review. Keep the source ZIP unchanged between inspection and extraction.
Open `reviews/EXAMPLE-saved/package/OPEN_ME_FIRST.html` if present; otherwise read the issue log
and available package tables. Validation updates `package_status.json` in the working copy; keep
the original ZIP unchanged.

The workbook result is advisory by default. For a required workbook, use the
strict check in [Read one saved package](../reader/03_READ_RESULTS.md).
