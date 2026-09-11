# How to Use Sapote-Mamey v9.7.428

The [README](../README.md) is the human landing page. Run `python mamey_run.py start` from
the extracted bundle root for the current command sequence. The [Quick Guide](GUIDE/02_Quick_Guide.md)
continues from installation through package review, BLASTp evidence, BiG-SCAPE, phylogeny,
figures, and Mode B. This page keeps the core operating contract in one short place.

## Standard workflow

```bash
python mamey_run.py doctor
python mamey_run.py inspect path/to/antismash_result.zip
python mamey_run.py run --strain EXAMPLE \
  --input-zip path/to/antismash_result.zip \
  --taxonomy 'Genus sp.' --source 'recorded isolation source' \
  --mode gold --outdir runs/
python mamey_run.py validate runs/EXAMPLE/package
python mamey_run.py explain runs/EXAMPLE/package
```

`manifest.json` is the package handoff object. The generated
`Project_Memory_Snapshot.json` is a compatibility alias for older handoff readers. Preserve the
package checksums, validation receipts, exact input identity, and any typed holds.

For a time-limited environment, add `--capped-session`. The full Sapote authoring protocol will not fit
into a small custom-instructions field; coding assistants should read the bundle's shared
[AGENTS contract](../AGENTS.md) and the current workflow document selected through
[CURRENT_DOCS_INDEX](../CURRENT_DOCS_INDEX.md).

## After validation

Use `discover` to inventory sealed packages and suggested next actions. Use `bgc-blastp-panel`,
`blastp-online`, or `blastp-round` to prepare protein searches, and `ingest-blastp` for retained
results. Use `bigscape` for a separately installed BiG-SCAPE workflow. Use `phylo-autopilot` for
16S routing and EPA-ng placement or `phylo-run` for an approved GToTree/IQ-TREE genome workflow.
Use `render-all-figures` as the normal figure entry point. Use `mode-b` to prepare a scaffold and
`verify-modeb` to check a finished authored card.

The [generated command catalog](COMMAND_CATALOG.generated.md) lists specialist and compatibility
commands. The [deliverable menu](DELIVERABLE_MENU.md) starts from the result a user wants rather
than from an internal command name.

## Evidence and interpretation boundaries

- Record BLASTp database name, release or access date, query identity, and retained raw result.
- Keep nr, ClusteredNR, Swiss-Prot, MIBiG, and BiG-SCAPE as distinct evidence channels.
- Treat unmeasured or unbound evidence as missing, not negative.
- Treat bioactivity as strain- or sample-level context unless an explicit experiment binds it to a locus.
- Treat a Mode B template as a scaffold. Authored interpretation and owner review remain separate.

## Audit workflow

For an adversarial code or patch audit, follow
[BUNNY_HOP_AUDIT_GAME.md](../debugging_modules/BUNNY_HOP_AUDIT_GAME.md). A "bunny hop" request
starts that audit protocol; its findings are review evidence, not release approval.

## Citation-Compact Provenance and Citation Status

Sapote-Mamey uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a handoff for a literature-search session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope.
