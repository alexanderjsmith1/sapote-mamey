# SOP-17 — cross-strain GCF cohort with BiG-SCAPE

To run a cohort, follow [Make BiG-SCAPE family tables and figures](../BIGSCAPE_COHORT_WALKTHROUGH.md). Setup and settings are in the [GCF workflow](../BIGSCAPE_GCF_WORKFLOW.md) and the [companion tool protocol](../LLM_COMPANION_TOOL_PROTOCOL.md). This page is the checklist to apply to a finished run.

A GCF (gene cluster family) is a group of BGC regions that BiG-SCAPE finds similar at one cutoff. See the [glossary](../GLOSSARY.md). A cohort family layer shows related architecture across strains. It does not assign compound identity, production, activity or novelty. It does not change a sealed package.

## Before the run

1. Pick the exact strains. Record each antiSMASH ZIP hash, its region count and its antiSMASH version.
2. Stage only region GBKs, with `tools/bigscape_prep.py`. Read `STRICTNESS_MANIFEST.tsv`. Every strain you expect must be `STAGED`, and every exclusion must have a row.
3. Choose the design. Cohort-only mode uses no references. A reference-augmented design adds MIBiG. Do not download MIBiG unless the user approves it.
4. State the plan first: region, strain and reference counts, the output folder, and the CPU setting.

## CPU setting

The interactive policy is one core. Pass it explicitly, because the two runners differ:

- `python mamey_run.py bigscape` takes `--cpus`. The default is 4, so pass `--cpus 1`.
- `tools/bigscape_pipeline.py` takes `--cores`. The default is 1.

Use two or four cores only when the user picks them.

## After the run

1. Choose one finished run. In the database, `select id, end_time from run;` must show an end time for it. Pass that ID as `--run-id` to every reader. A run with no end time is unfinished in the database, and its process may still be running. Check that the process for that output folder has exited and read `out/run.log` before you call it interrupted or retry. If you cannot tell, record it as unresolved. Reuse a cache only when the inputs and parameters are unchanged.
2. Check that the query-region count in the database equals your staged count. Check the integrity of the SQLite file.
3. Export the family table at each cutoff (0.3, 0.5 and 0.7 by default) with `tools/bigscape_family_verdicts.py`. Give each run and cutoff its own new table path. The tool refuses an existing table or `<table>.placement.tsv`, or a path equal to the database. If it is empty, compare counts before you read anything into it.
4. Keep the staged list, tool versions, the exact command, the cutoffs, the run ID and the output hashes beside the results.
5. If the user separately asks to add family context to Mode B cards or the triage board, do it as an addition. Keep the original card hashes. Do not change cards silently.

If a reader gives an empty or failed table, or the database holds several finished runs, see [BiG-SCAPE troubleshooting](../troubleshooting/BIGSCAPE_TROUBLESHOOTING.md).

## Portable join key

Join memberships on the run, the cutoff, the strain, the BGC alias and the contig and region. Use the database `family.id` for display only. It belongs to one database, run and cutoff. Never join two runs or databases by `family.id` or by viewer labels such as `FAM_#####`. The shipped family table carries `family_id` and `cutoff`. Record the run ID beside it.

## How to read families

Read a family as related architecture within this run. In cohort-only mode, never write KNOWN or NOVEL. In a reference run, say "MIBiG-anchored" or "unanchored in this panel".

## When to stop

Stop and report a hold. Do not improvise. Stop when:

- the HMM (Pfam) files are incomplete;
- region counts do not match;
- two files map to the same name;
- the run would exceed the approved resources;
- references need a download nobody approved;
- no single finished run can be named; or
- the user has not approved a change to a card.
