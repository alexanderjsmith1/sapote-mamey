# Gene evidence disagreement review candidate

A local browser view for checking where evidence channels disagree about a gene. It adjudicates nothing. Every cue needs a person to read it.

This is an experimental maintainer tool. It needs frozen evidence databases that you build or receive separately. It is not part of the first-run path (see [Your first run](reader/01_FIRST_RUN.md)).

## The six channels

The view compares six evidence channels. A selection must name all six.

| Channel | What it holds |
|---|---|
| `census` | The gene list for each region. This is the denominator. |
| `nr` | Protein search hits against NCBI nr (the general protein database). |
| `ClusteredNR` | Protein search hits against NCBI's clustered version of nr. |
| `SwissProt` | Protein search hits against the curated Swiss-Prot database. |
| `domain` | Protein domain annotations for each gene. |
| `MIBiG` | Alignments to MIBiG reference clusters. See the [glossary](GLOSSARY.md). |

## Run

You need Python 3.12 or newer, a bundle root, and a selection file.

```bash
python tools/evidence_disagreements.py --selection selection.json
```

The tool prints `Private local explorer: http://127.0.0.1:8767`. Open that address in a browser. The server binds loopback only, so nothing outside your computer can reach it. Use `--port` to change the port. A bad selection stops the run with a hold name such as `SELECTION_SCHEMA_OR_POPULATION_HOLD`.

To write a bounded source-review receipt instead of only browsing, add `--audit audit.json`. The path must not exist yet. If it appears during the run, the tool stops with `AUDIT_OUTPUT_EXISTS_CHOOSE_ADDITIVE_PATH` and writes nothing. The parent folder must already exist.

## The selection file

The selection is a JSON file. Relative paths resolve from the folder that holds it.

```json
{
  "schema": "mamey.disagreement-selection/1",
  "population": "EXAMPLE population label",
  "contract": {"path": "contract.md", "sha256": "<SHA-256 of contract.md>"},
  "sources": {
    "census":      {"root": "census",      "manifest": "RELEASE_MANIFEST.json", "manifest_sha256": "<SHA-256>"},
    "nr":          {"root": "nr",          "manifest": "RELEASE_MANIFEST.json", "manifest_sha256": "<SHA-256>"},
    "ClusteredNR": {"root": "ClusteredNR", "manifest": "RELEASE_MANIFEST.json", "manifest_sha256": "<SHA-256>"},
    "SwissProt":   {"root": "SwissProt",   "manifest": "RELEASE_MANIFEST.json", "manifest_sha256": "<SHA-256>"},
    "domain":      {"root": "domain",      "manifest": "RELEASE_MANIFEST.json", "manifest_sha256": "<SHA-256>"},
    "MIBiG":       {"root": "MIBiG",       "manifest": "RELEASE_MANIFEST.json", "manifest_sha256": "<SHA-256>"}
  }
}
```

- `population` is a label you choose for the gene set.
- `contract` points to a Markdown file with a 50-row table, one row per report section (`| 1 | requirement |` through `| 50 | ... |`). The SHA-256 must match the file.
- Each source needs a `root` folder, a `manifest` path inside it, and the manifest's SHA-256. Get the hash with `shasum -a 256 <file>`.
- The census pin is checked for four sources: `nr`, `ClusteredNR`, `SwissProt` and `domain`. Each manifest and its database metadata must name the selected census's SHA-256, or the tool stops with `MIXED_POPULATION_CENSUS_PIN_HOLD` or `CENSUS_DEPENDENCY_METADATA_HOLD`.
- The MIBiG source is not checked against the census. It opens under its own manifest and schema, and each record is shown only when its exact identity and source-member hash match the census gene's locus. That does not show the MIBiG database was built from the same population. Treat population equivalence for MIBiG as unverified.

## What you see

A search box and filters list the census genes 25 rows at a time. Open a gene to see each channel's raw statements, the source files and hashes, and any held items. Each retained search shows its lowest-ranked retained hit as a review representative only.

Review cues mark these differences:

- an unspecified annotation against a more specific one;
- a partial domain or module against a whole-protein call;
- wording that differs and is unresolved;
- a search that is missing;
- a recorded no-hit.

A cue never means a biological contradiction. A filter that returns no rows is not evidence of absence. A missing search and a recorded no-hit are shown as different states.

## Limits

- The view counts census gene occurrences as recorded, including overlaps. Genes from expanded boundary context are outside the count.
- A search hit counts only if its full locus identity, protein hash, locus tag and length match the census gene.
- KnownClusterBlast reference rows stay as held context. They carry no alignment-sequence proof.
- The page `mamey/evidence_disagreements.html` is a client for the running server. It is not a data export. The tool has no export, correction or evidence-index route. See [HTML template readers](HTML_TEMPLATE_READERS.md).
- The audit picks up to five distinct records by source state. It does not fail when fewer exist. The result key is `five_records`, so check the count inside it.
- The audit status `SOURCE_BOUND_ENGINEERING_REVIEW_ONLY` marks a mechanical snapshot. It is not a review of the whole population, and it does not accept any report section.
- The audit file does not record the hash of the selection file, the tool files or itself. Record those in a separate receipt, and write each audit to a new path.
- Source file stamps are checked on each request. Full digests are checked when the audit finishes.
