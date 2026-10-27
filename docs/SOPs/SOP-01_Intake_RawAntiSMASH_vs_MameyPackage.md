# SOP-01 — Intake: raw antiSMASH ZIP, Mamey package or reference accession

Use this SOP to decide what an uploaded ZIP is and which command comes first. Run commands from
the bundle root, the folder that holds `mamey_run.py` and `pyproject.toml`.

```bash
python mamey_run.py inspect <input.zip>
```

## Raw antiSMASH ZIP

A raw antiSMASH result usually contains `index.html`, `regions.js`, one or more `.gbk` files, one
or more `.region###.gbk` files, optional `.json`, and the `clusterblast/`, `knownclusterblast/` and
`subclusterblast/` folders. Run `inspect` first.

A full-genome result has many region GBKs, many ClusterBlast files and usually more than one BGC.
Run gold directly. Gold is the only analysis mode; `standard` is a deprecated alias and `smoke` is not accepted.

```bash
python mamey_run.py run --strain <ID> --input-zip <input.zip> \
  --taxonomy "<taxonomy, or unknown>" --source "<isolation source, or not supplied>" \
  --release <PUBLIC-or-PRIVATE> --outdir <new-run-folder> \
  --mode gold --capped-session --reference-completion off
```

`--capped-session` reduces the work done. It does not set a time limit and does not turn off
reference completion by itself, which is why the example adds `--reference-completion off`. Run
reference completion separately when you need it. If a run fails, keep its output and logs, and
rerun into a new folder.

## Single-region accession ZIP

Signs: one `.region001.gbk`, an accession-style sequence name such as `KY089035.1`, one BGC, and a
public accession instead of a private strain name. Run `inspect`, then check the source record and
its identity. Expect assembly warnings for a single region; they describe the input, not a failed
genome. Review each warning: an expected input shape does not clear content or provenance holds.
See [SOP-07](SOP-07_Single_Region_Public_Accession_Inputs.md).

## Sealed Mamey package

Signs: `manifest.json`, `checksums_sha256.txt`, workbooks, receipts and run metadata. Validate it;
do not rerun it as if it were raw antiSMASH output.

```bash
python mamey_run.py validate <package_dir>
```

`validate` rewrites `package_status.json`. Keep the original archive unchanged and validate an
extracted working copy.

`validate` prints a main result and a separate `WORKBOOK_CONTENT` result. By default the workbook
check is advisory: with no `*_5_workbook.xlsx` it prints `SKIP` and does not fail. With
`--workbook-strict`, a missing workbook prints `FAIL_WORKBOOK_MISSING` and the command exits
nonzero; a workbook whose content check fails also fails the command. If several workbooks match,
only the first in sorted order is checked. The populated-sheet check reads primary-key rows up to a
row cap, so a pass does not cover every cell. `--manifest-contract` adds an optional advisory manifest check.

## Public reference accessions

Label a public accession input as a reference sequence, control BGC, comparison BGC or parser test
fixture. Do not treat it as a private discovery strain. A public accession does not by itself set
the release label to PUBLIC.

<a id="inspector-and-validator-scope"></a>
## What `inspect` can and cannot tell you

`inspect` previews file names and markers and suggests a command. It does not check genome
completeness, taxonomy or extraction.

- Its suggested strain ID is cleaned from the ZIP filename. Check it against the archive and your
  metadata before you use it.
- Its region count includes only lowercase `.gbk` names containing `region` anywhere in the path.
  Uppercase `.GBK`, `.gbff` and `.gb` files are missed by the preview, though the parser reads them.
  A folder name containing `region` can also inflate the count.
- A high region count describes the archive's shape. It does not prove a whole-genome export.
  A zero preview count does not prove that supported source records are absent.
- Treat duplicate members, non-regular members, an unsupported schema, unknown strictness or an
  unresolved organism as intake warnings to review.
- A sealed package ZIP should be recognized from its manifest and checksums, then extracted. Do not
  rely on `inspect` to classify every ZIP.

## Checks for a bug hunt

1. `inspect` prints the archive type.
2. A single-region accession is reported as valid but limited.
3. A public accession does not trigger private AS/SID handling.
4. A sealed package is not treated as raw antiSMASH output.
5. Missing KnownClusterBlast output lowers evidence availability; it does not fail intake by itself.

## Related pages

[Workflow guide](../WORKFLOW_GUIDE.md) ·
[Single-region accession handling](../troubleshooting/SINGLE_REGION_ACCESSION_INPUTS.md) ·
[Batch intake](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md) ·
[Record-cap coverage](../ANTISMASH_INPUTS_CONSUMED.md#antismash-record-cap-coverage) ·
[Validation gates](../WORKFLOW_GATES_GUIDE.md)
