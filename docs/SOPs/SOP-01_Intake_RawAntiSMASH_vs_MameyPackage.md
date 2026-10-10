# SOP-01 — Intake: Raw antiSMASH ZIP vs Mamey Package vs Reference Accession

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


## Purpose

This SOP defines how Sapote/Mamey should classify uploaded ZIP files and choose the correct first command.

## Raw antiSMASH ZIP

A raw antiSMASH ZIP commonly contains:

- `index.html`
- `regions.js`
- one or more `.gbk` files
- one or more `.region###.gbk` files
- optional `.json`
- `clusterblast/`
- `knownclusterblast/`
- `subclusterblast/`

First action:

```bash
python mamey_run.py inspect <input.zip>
```

## Full-genome antiSMASH ZIP

Expected signs:

- many region GBKs,
- many clusterblast files,
- one or more source contigs,
- raw BGC count usually greater than 1.

Run gold mode directly in ChatGPT (gold has been the only analysis mode since v9.7.161 — `smoke`
was removed and `standard` is a deprecated alias of `gold`; `--capped-session` selects reduced evidence/render settings, but does not guarantee completion within any wall-clock budget or select a different mode):

```bash
python mamey_run.py run --strain <bound-ID> --input-zip <input.zip> \
  --taxonomy "<bound taxonomy or explicit unknown>" --source "<bound source or explicit unknown>" \
  --release <PUBLIC-or-PRIVATE> --outdir <fresh-run-root> \
  --mode gold --capped-session --reference-completion off
```

## Single-region antiSMASH accession ZIP

Expected signs:

- one `.region001.gbk`,
- one accession-style sequence name such as `KY089035.1`,
- one BGC,
- public accession rather than private strain name.

Run inspect first, then verify the actual source-record scope and identity. A successful preview does not validate content. Single-region inputs can produce assembly warnings that require limited-input interpretation; do not dismiss a warning solely because this input shape is expected.

## Sealed Mamey package

Expected signs:

- package manifest,
- checksums,
- workbooks,
- receipts,
- run metadata.

Preserve the original archive and select an extracted working package directory. Validation rewrites its mutable package-status receipt by default; it is not an entirely read-only intake step (`mamey/validate.py:1085–1106`). First action:

```bash
python mamey_run.py validate <package_dir>
```

Do not re-run the package as if it were raw antiSMASH input.

## Reference accession interpretation

Public accession inputs should be labeled as:

- public reference sequence,
- control BGC,
- comparison BGC,
- parser smoke fixture.

They should not be treated as private discovery strains.

## Bug-hunt checks

1. `inspect` should print archive type.
2. Single-region accession inputs should be called valid but limited.
3. Public reference accession should not trigger private AS/SID handling.
4. Sealed package should not be treated as raw antiSMASH.
5. Missing KCB should lower evidence availability, not necessarily fail intake.

## Intake does not certify execution or identity

`inspect` classifies filenames/markers and returns a suggested command. It does not prove genome completeness, successful extraction, taxonomy or release authority (`mamey/package_inspector.py:47–103,110–218`). Its strain suggestion is sanitized from the ZIP filename; review it against archive identity and supplied metadata before use (`:32–44,205–208`). A sealed-package ZIP must be classified by its manifest/checksum content and extracted for package readers; do not rely on `inspect` to distinguish every arbitrary ZIP.

A multi-region count is an input-shape observation, not proof of a whole-genome export. Duplicate member, nonregular member, unsupported schema, unknown strictness or unresolved organism warnings remain intake holds for review (`mamey/antismash_input.py:339–398`). Unknown provenance must stay explicit. Public accession shape does not automatically select PUBLIC release or resolve a strain record.

The example opts out of optional reference completion; select that compute separately when required and authorized. Capped mode otherwise can still run reference completion if its inputs are available (`mamey/cli.py:6150–6167`). On failure preserve outputs/logs and use a fresh reviewed destination rather than rerunning over a package. See [workflow guide](../WORKFLOW_GUIDE.md), [single-region identity handling](../troubleshooting/SINGLE_REGION_ACCESSION_INPUTS.md) and [batch directives](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md).

## Inspector and validator scope

`inspect` is a filename/marker preview. Its region count uses lowercase `.gbk` suffixes and the substring `region` anywhere in the member path. Uppercase `.GBK`, `.gbff` or `.gb` records can be missed by that preview even though the main GenBank parser supports them. A directory name containing `region` can also influence the preview count. A counted filename is not a successfully parsed BGC, and no counted regions does not by itself prove an archive lacks supported source records. Reconcile the actual regular-member inventory, parser diagnostics and bound input scope before deciding that an upstream rerun is needed.

For an extracted package, keep validation results separate from upstream scan coverage and requested-output completeness. The CLI prints a main result and a separate `WORKBOOK_CONTENT` result. Workbook checks are advisory by default; `--workbook-strict` makes a non-PASS result block the command when a matching workbook is found. It does **not** require a workbook to exist: with no `*_5_workbook.xlsx`, the CLI prints `SKIP` and that workbook branch does not block success. With several matching files it checks only the first in sorted order. If your task requires a workbook, independently confirm the exact expected path/current run and its receipt, then review its full schema, roster and values. The populated-sheet check examines primary-key rows under a configured row cap; it does not certify all workbook content.

Preserve both printed results, exit status, current input/package hashes and unresolved warning states. `--manifest-contract` is an optional additional check, not a substitute for input identity or scan coverage. Validation can update mutable status receipts, so use an authorized extracted working package while retaining the original archive. See [record-cap coverage](../ANTISMASH_INPUTS_CONSUMED.md#antismash-record-cap-coverage) and [current validation gates](../WORKFLOW_GATES_GUIDE.md).

Sources: `mamey/package_inspector.py:47–103,110–218`, `mamey/parsers.py:378–389`, `mamey/cli.py:4552–4578` and `mamey/validate.py:1135–1225`.
