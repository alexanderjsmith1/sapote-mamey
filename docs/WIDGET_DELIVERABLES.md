# Interactive widget deliverables

The named builder is `render-widgets`. It reads a package directory, a run directory containing `package/manifest.json`, or a ZIP with the required package manifest and writes a separate reader bundle. Choose a reviewed source with its validation and integrity evidence; the renderer itself does not require proof that it is sealed or scientifically accepted.

From the bundle root, this is a command template; substitute reviewed absolute paths:

```bash
python3 mamey_run.py render-widgets --package /ABSOLUTE/PATH/TO/Complete_Package.zip --outdir /ABSOLUTE/PATH/TO/widgets
```

Without `--outdir`, output is `<source-name>_widgets` beside the source (ZIP extension omitted). Explicit output resolves symlinks and is rejected when it equals or lies beneath the resolved package directory. For a run-directory input, the protected root is its `package/` directory. The default does not imply permission to overwrite an existing reader deliverable.

## Views and files

Open `OPEN_WIDGETS.html`. The seven view pages are:

| File | View |
|---|---|
| `priority.html` | BGC priority, tier/boundary filters and routing scores |
| `domains.html` | Domain architecture/counts |
| `evidence.html` | CCTT and KCB evidence and guards |
| `genes.html` | Gene-level evidence overview |
| `rggmci.html` | Candidate relationships, with no physical-linkage claim |
| `completeness.html` | Missing worklist and package/gate/claim states |
| `gene.html` | Individual gene evidence reader using the separate package-native roster model |

The two gene pages are not equivalent evidence-admission reports. `genes.html` uses the current gene-by-gene CSV with positive amino-acid lengths; duplicate `(bgc_id, locus_tag)` keys are quarantined. BLASTp rows require the current strain/BGC/locus and matching positive amino-acid length. Inspect `widget_data.json` → `gene_evidence_receipt`, including duplicate and admitted/held counts. `WIDGET_MANIFEST.json` → `counts.gene_rows` counts this model only.

`gene.html` instead uses `gene_roster`, built from inventory, `locus_maps/*_locus_data.csv` and channel stores. Its gene membership can include channel-only rows, and its first selected channel row has different precedence from `genes.html`; it does not enforce that page's current-strain/amino-acid-length admission. Legacy online nr/clustered-nr labels are accepted interchangeably by this roster reader. Reconcile full `strain / full node-or-contig / region / BGC alias`, current gene membership and actual channel provenance before reusing either display. A populated legacy roster is not proof that a corresponding exact-current hit was admitted. Missing roster geometry/channels can yield an empty individual-gene view while the gene overview contains rows.

Additional files include `widget_data.json`, `PUBLICATION_HANDOFF.md`, `publication_metadata.json`, `README.md`, `WIDGET_MANIFEST.json` and `SHA256SUMS.txt`. The HTML embeds its data and requires no external JavaScript, server or network. Browser display and export denominators differ: the priority table renders at most 250 filtered rows; the RG-GMCI chart displays 25 filtered pairs and its table at most 500. Their filtered CSV buttons export the full filtered arrays. A label saying rows are “shown” can therefore exceed the visible table. Record filter settings, visible/chart limits and actual exported row count; do not infer whole-roster coverage from a screenshot. Exports are browser-created files separate from the renderer's output/checksum manifest, so retain their own hashes and provenance. SVG/CSV export and displayed scientific content still require browser and reader review before publication. Inspect the actual generated pages and preserve the browser-review record.

## Input, status and integrity scope

`manifest.json` is required. Most evidence tables/status files are optional; absent inputs can leave empty views while rendering succeeds. Missing evidence is not a biological zero or a completed search. Duplicate matching artifacts, invalid JSON objects, malformed CSV headers or row widths fail rather than silently selecting a source. Inspect `source.artifacts`, row counts, source status and the missing worklist. The missing worklist is a supplied package table, not a newly computed check of every evidence category. The priority model iterates the triage table when it has rows, otherwise the inventory; a partial nonempty triage table is not automatically completed from the inventory. Its displayed rank is a newly sorted/renumbered `1..N` navigation rank, not an unchanged package rank. Compare the actual triage/inventory roster and preserve source ranks separately.

Some absent numeric cells are represented by display defaults: blank AB/AF/novelty/length cells and blank domain counts can become zero. That zero is not a measured value or evidence of biological absence. Check the raw source and `domain_coverage` in `widget_data.json` before interpreting or exporting these defaults; retain typed missingness in downstream evidence.

The renderer snapshots all files beneath the selected package root, or the complete ZIP bytes, and checks that snapshot before completion. Its reported `source.fingerprint` is a separate SHA256 aggregation of the **consumed artifact names and hashes**, not the whole ZIP's SHA256 and not a release-validation result. Record the source path and independently retained package/ZIP hash alongside it.

Widget `PASS` means the render completed with equal consumed-artifact fingerprints and passed the source snapshot check. It does not prove every evidence layer exists, validate the extraction package, upgrade Mode B judgment, or establish biological, figure or publication acceptance. The command returns 0 for widget `PASS`, 1 for a caught missing/invalid source or a non-PASS manifest; other filesystem exceptions may propagate. Read receipts rather than relying only on exit status.

## Reuse and interruption recovery

The output directory can already exist. Known output files are replaced atomically one file at a time; before writing, the renderer removes old `WIDGET_MANIFEST.json` and `SHA256SUMS.txt`. A failed refresh may leave partial new pages and old untracked files. Once marker invalidation has occurred, a failure in the guarded writing block removes completion markers but does not restore the prior bundle or clean unrelated files. Source/model validation and page preparation occur before that invalidation; an early failed refresh can leave the previous successful bundle and its completion markers intact. Verify the receipt's source fingerprint/artifact bindings and the current invocation's status. Existing markers alone do not prove the new attempt completed. The final output manifest includes all top-level files already present, except its two completion markers; checksum output includes the manifest. Consequently, use a dedicated output directory, review preexisting files, and preserve the accepted prior deliverable before a governed refresh. Do not treat surviving HTML alone as completed output.

After interruption, inspect the error and source identity in place. Retain partial output as unaccepted evidence until reviewed; use an explicitly selected clean reader-output directory for a new attempt when authorized. Never repair a source package by deleting or moving its evidence to satisfy this reader.

## Publication handoff

The handoff provides captions/methods templates, SVG/CSV export guidance, citation status and claim ceilings. Unresolved dataset and biological citations remain `citation_needed`; Sapote-Mamey attribution is operator supplied. The included antiSMASH citation label is renderer metadata, not confirmation of the selected input's version. Check the exact source/tool version and citations before sharing.

Source owners: `mamey/widget_deliverable.py:190–238,244–331,691–712,1148–1238`; CLI flags `mamey/cli.py:6405–6418`. See [artifact maps and menu limits](ARTIFACT_MAP_LIMITS.md) and [the deliverable contract](DELIVERABLE_CONTRACT.md).
