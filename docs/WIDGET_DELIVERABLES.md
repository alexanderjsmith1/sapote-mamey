# Browse a package with widgets

Create linked, offline HTML pages from an extracted package, its run folder or
its Complete_Package ZIP. Run this from the program folder, replacing `EXAMPLE`:

```bash
python mamey_run.py render-widgets --package runs/EXAMPLE/package
```

The default output is `runs/EXAMPLE/package_widgets/`. For another source, the
name is its filename plus `_widgets`, without `.zip`. Use `--outdir` only to
choose another folder. It must be outside the package, including after resolving
symlinks. Choose a new folder for a rerun so previous pages stay intact.

## Open the reader

Read `WIDGET_MANIFEST.json` for the source and row counts, then open
`OPEN_WIDGETS.html`. The pages embed their data and need no server or network.

| Page | What to inspect |
|---|---|
| `priority.html` | Priority, tiers, boundaries and routing scores |
| `domains.html` | Domain architecture/counts |
| `evidence.html` | CCTT and KCB evidence |
| `genes.html` | Gene-evidence table |
| `gene.html` | One gene from the package-native roster |
| `rggmci.html` | Candidate fragment pairs |
| `completeness.html` | Saved missing-evidence worklist and states |

The folder also has `widget_data.json`, `README.md`, `SHA256SUMS.txt`,
`publication_metadata.json` and `PUBLICATION_HANDOFF.md`.

## Check a number before reusing it

Blank AB/AF, novelty, length and domain-count cells display as **0**. Check the
raw table and `domain_coverage` in `widget_data.json` before treating that as a
measurement. An absent table instead produces an empty view. Only the manifest
is required; malformed or duplicate source artifacts stop rendering.

The priority view uses a nonempty triage table, otherwise the inventory. It
renumbers ranks and does not fill a partial triage table from the inventory.
The worklist is copied from the package rather than newly computed.

The priority screen shows at most 250 filtered rows. The pair chart shows 25
and its table 500. “Export filtered CSV” exports all filtered rows, so record
the filters and export count. Browser-created CSV/SVG exports are outside the
renderer manifest and checksums; save their hashes separately.

## Why the gene pages can differ

`genes.html` requires positive protein lengths and sets aside duplicate
`(bgc_id, locus_tag)` keys. BLASTp rows must match strain, BGC, gene and length.
Read `gene_evidence_receipt`; `counts.gene_rows` counts this page only.

`gene.html` combines the inventory, locus-map data and channel stores. It can
include channel-only genes and does not apply those same strain/length checks.
The first selected channel row wins; tagged overlays precede TOP10 rows and
untagged overlays are skipped. The page displays nr, Swiss-Prot, MIBiG and
ClusterBlast; clustered-nr and EBI fields are also in `widget_data.json`.
Missing roster geometry can leave this page empty while `genes.html` has rows.

Before using either view, check **strain / full node-or-contig / region / BGC
alias**, gene membership and channel source against the package.

## Check completion and recover

The renderer checks that the package files or ZIP stayed unchanged during the
run. `source.fingerprint` hashes consumed filenames and file hashes; record the
original archive/package hash too. Widget PASS describes this render, so check
the source package's validation separately.

Exit 0 means PASS; 1 means a missing/invalid source or a non-PASS manifest.
Other filesystem errors can raise exceptions. Read the manifest and terminal
output. Never remove source evidence to get past an error.

An existing output folder is refreshed file by file. The renderer first removes
its old manifest and checksum file; an interrupted refresh can mix old and new
pages without completion files. Earlier failures can leave the old completion
files untouched. Unrelated files remain and enter the new top-level manifest.
Keep a previous accepted output and retry in a clean folder after fixing the error.

## Share the result

Fill the dataset and biological `citation_needed` fields and the
`operator_supplied` software attribution. Check the actual antiSMASH version:
the printed citation is a fixed label. Review the pages in a browser and check
the caption/Methods templates before sharing. See [artifact map limits](ARTIFACT_MAP_LIMITS.md)
and the [deliverable contract](DELIVERABLE_CONTRACT.md).

<a id="the-two-gene-pages-use-different-rules"></a>
<a id="what-the-pages-show-and-what-they-leave-out"></a>
<a id="status-and-integrity"></a>
<a id="re-running-into-an-existing-folder"></a>
<a id="publication-handoff"></a>
