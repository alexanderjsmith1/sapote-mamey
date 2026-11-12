# Saving a Mode B card in the register

This page is for scripts and maintainers. If you are writing a card by hand, use the [Mode B walkthrough](../MODE_B_USER_WALKTHROUGH.md) and its `ingest-receipts --card` command instead. For terms such as card and package, see the [glossary](../GLOSSARY.md).

`mamey.judgment_store.record_mode_b` saves a card as a file in the package and adds a row to the register. It runs an older quality check and records the result. It does not run `verify-modeb`.

## Call it

Run from the bundle root so `mamey` imports:

```python
from mamey.judgment_store import record_mode_b

result = record_mode_b(
    package_dir="runs/EXAMPLE/package",
    bgc_id="BGC_ID_FROM_INVENTORY",
    mode_b_md=open("card.md").read(),
    session_id="manual",
    rank=1,
    edge_status="Interior",
    cds_count=30,
)
print(result["persistence_warnings"])
```

The card must open with its exact identity, `# Mode B — <strain> / <full node-or-contig> / <region> / <BGC alias>`, matching the package's triage-board row and the manifest's `strain_id`. If the header is missing, incomplete or appears twice, if any part conflicts with the package, if the alias has no triage-board row, or if the board cannot be read, `record_mode_b` raises `ModeBIdentityHold` before it writes anything: no card, no reader note, no register row. The exception's `exit_code` is 2, `components` names the parts involved (strain, full contig, region, alias), and its message gives the card and package values. Fix the card header from the package inventory and call again. The `ingest-receipts` routes run their own identity check first and are not changed.

`rank`, `edge_status` and `cds_count` come from the package inventory. They set which character floor the check applies. `layperson_paragraph` and `fermentation_note` are optional and default to empty. The function returns a dict with `path`, `verdict` and `persistence_warnings`. In the default direct call, the identity gate can refuse before writing; quality and claim-safety findings are advisory. Other validation or I/O errors can still stop the call. The `identity_checked_by_caller` bypass is reserved for routes that perform their own gate. The quality tier and the claim-safety linter result are recorded in `verdict` (`verdict["tier"]`, `verdict["claim_safety"]`), and the card is written even when the linter finds a problem. Read the `verdict` fields as well as `persistence_warnings`, and open the files it names. For hand-written cards, prefer the gated `ingest-receipts --card` route.

## Files it writes

The card and the reader notes are under `<package>/judgment/`. The register and its `.last-good` backup are at the package root:

| File | Contents |
|---|---|
| `<strain>_<alias>_mode_b.md` | the card; replaced on each call |
| `<strain>_laypersons_section.md` | reader notes; a nonempty note replaces the section under `## <BGC alias>`, or is appended if there is none |
| `<strain>_fermentation_section.md` | reader notes; same rule |
| `<package>/<strain>_judgment_register.json` (package root, not `judgment/`) | one row per cluster, with a `.last-good` backup |

Preserve reader notes before updating. For duplicate headings of the same alias, the upsert writes the new note at the first heading and removes later matching sections; it does not merge their contents. Blank optional notes do not replace existing sections.

The alias is a lookup name within one package. It is not a unique locus ID.

## The register

A row gets `status=COMPLETE` and a `quality_tier` of `FULL`, `SHALLOW`, `STUB` or `UNKNOWN`. A thin card still counts as COMPLETE. `completion_pct` counts that status only. The register stores a file name, not a hash, so an edit to the card makes the stored tier stale.

The card, optional reader notes, register, last-good snapshot and banner are separate operations. Snapshot/banner failures can be persistence warnings; other failures can leave partial results. Repeating a call replaces the card and the reader-note sections for that alias. If a call stops partway, some files can be new and others old, so check the files before you retry.

## What to run afterward

`record_mode_b` does not run profile verification. Inspect `result["path"]` and verify that actual saved path against the bound package and alias. The example below assumes it returned `runs/EXAMPLE/package/judgment/EXAMPLE_BGC_ID_FROM_INVENTORY_mode_b.md`; substitute the real returned path, quoting spaces:

```bash
python mamey_run.py verify-modeb runs/EXAMPLE/package/judgment/EXAMPLE_BGC_ID_FROM_INVENTORY_mode_b.md --package runs/EXAMPLE/package --bgc BGC_ID_FROM_INVENTORY
```

Add `--contract current50_v2` for that profile. Read every ERROR and WARN. Batch progress and completion checks are on the [batch page](MODE_B_BATCH_RUN.md).

Workbook write-back functions read the register. They add no verification of their own, so back up the workbook first.
