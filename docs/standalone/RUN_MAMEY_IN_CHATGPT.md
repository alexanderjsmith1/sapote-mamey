# Run Mamey v1.9.152 in ChatGPT

## Upload checklist

Upload:

1. `Mamey_v1.9.98_Standalone_ChatGPT_Bundle.zip`.
2. One to three antiSMASH ZIPs for the current extraction batch.
3. An existing Mamey master workbook if this is a continuation; otherwise Mamey will create one.
4. Optional metadata table with strain ID, taxonomy, source, and assay notes.

## Operator prompt

Copy/paste this after upload:

```text
Run Mamey v1.9.152 Standalone ChatGPT Bundle on the uploaded antiSMASH ZIPs. Use batch mode if needed. Produce the updated master workbook, per-strain complete packages, combined output ZIP, summary CSV/MD, validation status, and clear deferred ledger. Do not call the judgment layer complete unless every BGC has a Mode B card or ledger entry.
```

## Execution order inside ChatGPT

1. Inspect the bundle and input ZIPs.
2. Run tests or smoke import where practical.
3. Run extraction batch with `mamey_run.py`.
4. Validate each per-strain package.
5. Create or update the master workbook.
6. Create a combined output ZIP.
7. Summarize: strain, raw BGCs, corrected BGCs, assembly tier, scan status, top lead, package validation state.
8. State what remains for the judgment layer.

## Batch continuation prompt

```text
Continue Mamey v1.9.152 on the next batch. Use the current master workbook and preserve all prior rows. Proceed in batches and package outputs after each batch.
```

## Judgment continuation prompt

```text
Continue from the Mamey manifest(s). Run full Mode B judgment for the next batch of BGCs. Preserve the locked BGC IDs and do not rerun extraction unless the manifest is invalid.
```

## Practical notes

- Prefer `--json-evidence off` unless a small JSON or bounded JSON requirement is explicit.
- Do not force many large antiSMASH ZIPs through one execution pass.
- If a run times out after producing partial strain outputs, rerun the batch cleanly with the same master path or resume from the last validated package.
- Treat missing full-proteome evidence as a CGAD/cassette confidence limitation, not as a biological absence call.

