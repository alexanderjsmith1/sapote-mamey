# Make a compact citation report

Add a citation ledger, a compact lead table and literature-search instructions
to an extraction. You need an antiSMASH result ZIP and the installed program.
This runs the extraction again; the separate output folder keeps an earlier run intact.

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --token-budget citation-compact --outdir runs/citation
```

`--token-budget` selects these supplements. `--outdir` puts this run under
`runs/citation/EXAMPLE/`; other run settings use their defaults.

## Open the outputs

Open the compact reports and `CITATION_COMPACT_QA.json` under
`runs/citation/EXAMPLE/package/citation_compact/`. The package root holds
`Citation_Ledger.csv` and `.json`.
If the compact folder is absent, check `run_phase_receipts.jsonl` for an error;
this optional phase can fail while the extraction continues.

The lead table puts scope, evidence, citations, uncertainty and a proposed next
experiment in separate fields. Copy the complete **strain / full node-or-contig /
region / BGC alias** from the package inventory; a generated lead label can change.

`Literature_Search_WorkOrder.md/json` lists the searches still needed. It does
not run them. Review the proposed experiments before using them.

## Citation-Compact Provenance and Citation Status

Method references describe antiSMASH 8.0 (`10.1093/nar/gkaf334`) and MIBiG 4.0
(`10.1093/nar/gkae1115`). They support the methods, rather than every lead's interpretation.

- `operator_supplied`: carried from existing package evidence or comparator fields.
- `citation_needed`: literature support still needs to be found and checked.
- `verified` and `not_applicable`: source-status labels; check the supporting record.
- `PASS_STRUCTURE`: the emitter's priority-citation and repeated-caveat checks found
  no error. Read warnings and verify the cited passages separately.

`interpretation_scope` states the lead's intended reading scope. Keep the common
genome-mining caveat once across the compact reports. See
[report readers](CITATION_COMPACT_READERS.md) for the separate package gate and its
file/schema/checksum checks. Work on a writable copy when revising compact outputs:
the emitter replaces its fixed filenames.
