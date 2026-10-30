# Group BGCs with BiG-SCAPE

BiG-SCAPE groups selected antiSMASH regions into gene cluster families (GCFs).
You need region GenBank files, BiG-SCAPE, Pfam and its pressed HMM files.
Use the [cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md) for the bundled
launcher. This page explains the input choices and checks behind that sequence.

## Choose the comparison

A cohort-only run compares your selected regions. A reference run also includes
MIBiG or another named reference collection. Record the reference version and
which records loaded; acquire new reference data only when that work is approved.

Use antiSMASH **region GBKs** from the source ZIPs. Whole-genome FASTA files and
Mamey CSV tables are different inputs. Keep a roster with each ZIP path/hash,
member path/hash/size, full **strain / node-or-contig / region / BGC alias**,
antiSMASH version when available, and cohort/reference role.

## Check the installation

```bash
python mamey_run.py doctor --companions
```

Check the installed BiG-SCAPE version and help before choosing its options.
Pfam requires `Pfam-A.hmm` and matching `.h3f`, `.h3i`, `.h3m` and `.h3p` files.
The checked BiG-SCAPE 2.0.3 route can call lowercase `fasttree` where an environment
provides `FastTree`; if a run-local alias is needed, record it with the run.

Read [the companion protocol](LLM_COMPANION_TOOL_PROTOCOL.md) for the preflight
and resource budget. The cohort walkthrough supplies a one-core example.

## Select settings deliberately

The workflow uses region records, category classification, visible singletons
and cutoffs 0.3, 0.5 and 0.7. Record these choices with the exact executed command.
Leave alignment at the default `auto` for mixed complete/fragmented regions;
forcing global alignment can change how fragments compare. A selected local-mode
comparison is a different analysis and needs its own recorded settings.

For a cohort-only run, omit MIBiG and other reference options. In the checked
2.0.3 interface, `-m/--mibig-version` can acquire MIBiG; `-r/--reference-dir`
selects other reference GBKs. Verify loaded counts, especially when reference
filenames lack `region` or `cluster`.

## Check staging before clustering

The prep tool copies region bytes to strain-prefixed filenames. It requires an
explicit strictness choice, or a justified mixed-input override, and a fresh
output directory. It skips hard-excluded strains by default.

Inspect the files, errors, exclusions and strictness manifest together. An input
failure can leave earlier staged files even when that input's count is zero;
collisions do not roll back earlier files. Add the source-member/hash/identity
roster because the prep tool does not generate it for every accepted member.
Estimate substantial staging space first and keep the source archives in place.
When two inputs collide, store one content-addressed copy and link it under each
strain-prefixed name.

## Resume and select the completed run

Before retrying, read the state, log tail, database integrity result and cached
record counts. Resume only with the same inputs and scientific settings.

Select the completed database run using its parameters and expected membership;
never use `max(run.id)`, because the largest run ID can belong to a failed attempt. The pipeline requires an
explicit run ID for existing databases and for `--skip-cluster`.
`--skip-prep` requires separately checked prepared inputs; chunked MIBiG is refused.

Family IDs and viewer labels are local to a database/run. Across runs, join on
full biological identities and reference accessions, keeping the source run and
cutoff for every membership.

## Read and export the result

Check staged/database region counts, strain coverage, exclusions, CDS/domain-hit
counts, comparison coverage and family memberships at each cutoff. Count eligible
**region** records, not their candidate-cluster or protocluster subrecords.

Distinguish measured singletons from failed, excluded or unmeasured records.
Panel composition and fragmentation affect family sharing, so a singleton is
not a novelty result. Record contig-edge status when fragmented regions contribute
to a count. Compare candidate split relationships using their full identities
and supporting records before proposing a combined count.

Export a table keyed by cutoff, source run ID and full locus identity. Keep the
database, integrity result, command, settings, logs, memberships and output hashes.
Describe family membership as similarity within that sampled comparison.
Only a user-approved, source-preserving reconciliation adds this context to Mode B
cards or the triage board; write overlays and leave sealed cards unchanged.

## Implemented adapters versus the requested runbook

The requested run records are `RUN_MANIFEST.json`, `RUN_STATE.json`, `COMMAND.sh`,
`EVENTS.jsonl`, `HANDOFF.md`, a QA report and hashes. The prep/pipeline adapters do
not automatically create the whole set. Record missing items explicitly.

The pipeline emits legacy known/novel tables even without MIBiG. Read them with
the actual reference-loading and comparison evidence. Its optional ingest rewrites
package cards; use a preserved working package and review the changes before
integration. See [integration limits](BIGSCAPE_MAMEY_INTEGRATION.md) and
[recovery](troubleshooting/BIGSCAPE_TROUBLESHOOTING.md).
