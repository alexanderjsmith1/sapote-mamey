# Interactive widget deliverables

`render-widgets` turns an existing package into a set of linked, offline HTML pages for browsing. It reads a package folder, a run folder that contains `package/manifest.json`, or a Complete_Package ZIP.

```bash
python3 mamey_run.py render-widgets --package /ABSOLUTE/PATH/TO/Complete_Package.zip --outdir /ABSOLUTE/PATH/TO/widgets
```

Without `--outdir`, output goes to `<source-name>_widgets` beside the source (the `.zip` is dropped from the name). The output folder may not be the package folder or inside it; symlinks are resolved first. For a run folder, the protected folder is its `package/`. Use a new, dedicated output folder.

## Open the reader

1. Read `WIDGET_MANIFEST.json`. Check the source path, the artifact bindings and the row counts.
2. Open `OPEN_WIDGETS.html` and pick a view.
3. If a view is empty, check `widget_data.json` and the source table before deciding the evidence is absent.

| File | View |
|---|---|
| `priority.html` | BGC priority, tier and boundary filters, routing scores |
| `domains.html` | Domain architecture and counts |
| `evidence.html` | CCTT and KCB evidence and guards |
| `genes.html` | Gene-level evidence overview |
| `rggmci.html` | Candidate RG-GMCI pairs; no physical-linkage claim |
| `completeness.html` | Missing-evidence worklist; package, gate and claim states |
| `gene.html` | One gene at a time, from the package-native gene roster |

Other outputs: `widget_data.json`, `PUBLICATION_HANDOFF.md`, `publication_metadata.json`, `README.md`, `WIDGET_MANIFEST.json` and `SHA256SUMS.txt`. The pages embed their data and need no server, network or external JavaScript.

## The two gene pages use different rules

- `genes.html` uses the current gene-by-gene CSV. Rows need a positive amino-acid length. Duplicate `(bgc_id, locus_tag)` keys are set aside. BLASTp rows must match the current strain, BGC, locus and length. `widget_data.json` → `gene_evidence_receipt` gives the admitted, held and duplicate counts. `WIDGET_MANIFEST.json` → `counts.gene_rows` counts this page only.
- `gene.html` uses `gene_roster`, built from the inventory, `locus_maps/*_locus_data.csv` and the channel stores. It can include genes that appear only in a channel, and it does not apply the strain and length checks above. The first selected channel row wins;
tagged overlay rows take precedence over TOP10-store rows. Overlay rows need a matching channel tag; untagged rows are skipped. `nr` and `clustered_nr` stay separate. The page shows nr, Swiss-Prot, MIBiG and ClusterBlast; the roster also carries clustered-nr and EBI fields, visible in `widget_data.json`.

The two pages can disagree. `gene.html` can be empty when roster geometry is missing while `genes.html` has rows. Before reusing either, confirm the full `strain / full node-or-contig / region / BGC alias`, gene membership and channel source.

## What the pages show and what they leave out

- **Display limits.** The priority table shows at most 250 filtered rows. The RG-GMCI chart shows the top 25 filtered pairs and its table at most 500. The "Export filtered CSV" buttons export every filtered row, so the "shown" count can exceed what is on screen. Record your filters and the exported row count.
- **Exports are yours to track.** Browser-made SVG and CSV files are not in the renderer's manifest or checksums. Hash them yourself.
- **Blank numbers become zero.** Blank AB, AF, novelty, length and domain-count cells display as 0. That 0 is not a measurement. Check the raw table and `domain_coverage` in `widget_data.json`.
- **Ranks are renumbered.** The priority view uses the triage table when it has rows, otherwise the inventory, and renumbers ranks 1..N. A partial triage table is not filled in from the inventory. Keep the package's own ranks separately.
- **Missing inputs are allowed.** Only `manifest.json` is required. Absent tables give empty views, not zeros. Duplicate matching artifacts, invalid JSON, or malformed CSV headers or rows stop the render.
- **The worklist is copied, not computed.** The missing-evidence worklist is a table from the package, not a fresh check of every category.

## Status and integrity

The renderer snapshots every file under the package root, or the whole ZIP, and checks that snapshot before it finishes. `source.fingerprint` is a SHA-256 over the names and hashes of the files it consumed. It is not the ZIP's own hash. Record the source path and the package or ZIP hash alongside it.

Widget `PASS` means the render finished and the source did not change during it. It does not show that every evidence layer exists or that the package is valid. It does not change Mode B judgment and is not figure or publication approval.

Exit codes: 0 for `PASS`; 1 for a missing or invalid source or a non-`PASS` manifest. Other filesystem errors can surface as exceptions. Read the manifest, not only the exit code.

## Re-running into an existing folder

The output folder may already exist. Before writing, the renderer deletes the old `WIDGET_MANIFEST.json` and `SHA256SUMS.txt`, then replaces known files one at a time.

- If a refresh fails partway, new and old pages can be mixed and the two completion files are absent. Old unrelated files are not cleaned up.
- If it fails before writing starts, the previous output and its completion files stay intact.
- The new manifest lists every top-level file already present, including leftovers. The checksum file includes the manifest.

So: use a dedicated folder, look at what is already there, and keep a copy of any accepted earlier output before refreshing. HTML on disk alone does not mean the latest run finished.

After an interruption, check the error and the source in place. Keep partial output until it is reviewed, and start again in a clean folder. Never delete or move package evidence to make the reader run.

## Publication handoff

`PUBLICATION_HANDOFF.md` gives caption and methods templates, SVG/CSV export guidance, citation status and claim limits. Dataset and biological citations stay `citation_needed` until filled. Sapote-Mamey attribution is `operator_supplied`. The antiSMASH citation it prints is a fixed label, not a check of the input's antiSMASH version. Confirm the real tool versions and citations, and review the pages in a browser, before sharing.

See [artifact maps and menu limits](ARTIFACT_MAP_LIMITS.md) and [the deliverable contract](DELIVERABLE_CONTRACT.md). The code lives in `mamey/widget_deliverable.py` and `mamey/roster_v2.py`; the CLI entry is `render-widgets` in `mamey/cli.py`.
