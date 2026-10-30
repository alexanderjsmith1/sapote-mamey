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

A Complete_Package ZIP contains `package/manifest.json`, checksums and
`package/OPEN_ME_FIRST.html`. Extract it into an unused working folder; extraction can replace files there:

```bash
python -m zipfile -e ~/Downloads/AS-40_Complete_Package.zip reviews/EXAMPLE-saved
python mamey_run.py validate reviews/EXAMPLE-saved/package
```

Open `reviews/EXAMPLE-saved/package/OPEN_ME_FIRST.html` and read the workbook and
issue log. Validation updates `package_status.json` in the working copy; keep
the original ZIP unchanged.

The workbook result is advisory by default. For a required workbook, use the
strict check in [Read one saved package](../reader/03_READ_RESULTS.md).
Saved packages use this route: `inspect` can reject them as an unrecognized input.

<a id="inspector-and-validator-scope"></a>
