# Enzyme neighborhood explorer

This optional tool builds a local HTML view of the genes around loci that already carry a DKP or CDPS call. It reads evidence you pin; it runs no new scan or sequence search and copies no database. The result is a candidate view for review. It is not a finding.

- **DKP**: diketopiperazine, a small cyclic dipeptide product class.
- **CDPS**: cyclodipeptide synthase, the enzyme family that makes many DKPs.
- **Owner candidate**: a locus whose source call state is `OWNER_DKP_CDPS_CANDIDATE`.
- **Tested-no-call**: a locus whose source call state is `TESTED_NO_OWNER_CALL`. It was checked and had no call. It is a contrast case, not evidence of absence.
- **current50**: the 50-section card requirements table, supplied as a Markdown source file you pin in the config (`current50_contract`). The view reports which sections its data can address. It never marks a section complete.

Other terms are in [the glossary](GLOSSARY.md). Setup is in [the first-run recipe](reader/01_FIRST_RUN.md).

## What you need

Run from the bundle root, in a bundle that includes the shared database-inspection code (`tool_database_reader`). You also need these frozen, hash-pinned sources:

| Config key under `sources` | What it is |
|---|---|
| `dkp_manifest`, `dkp_database`, `dkp_reader` | DKP evidence manifest, its SQLite database, and the Python reader file |
| `architecture_manifest`, `architecture_database`, `architecture_reader` | Gene architecture manifest, database and reader file |
| `census_manifest`, `census_database` | Gene census manifest and database |
| `domain_manifest`, `domain_database` | Domain manifest and database |
| `current50_contract` | The 50-section requirements table (Markdown) |

The reader files run as code after their hash is checked. A matching hash is not a sandbox. Pin only reader files you trust.

Each reader is a Python file that defines a `read` function:

- DKP reader: `read(database, manifest_sha256, identity, kind, limit, offset, include_raw=True)`. The kinds are `loci`, `genes`, `cds_context` and `domains`.
- Architecture reader: `read(database, identity, kind, limit, offset, include_qualifiers=False)`. The kinds are `genes` and `features`.
- Census and domain databases go through the shared `inspect_tool_database` check with `gene-census-v1`. They need no reader key.

The tool does not search for evidence or pick a newest file. Every source is one you name in the config.

## Config file

Save this as `view-config.json`. Replace each `sha256` with the file's SHA-256 (`shasum -a 256 <file>`).

```json
{
  "allowed_output_root": "/abs/path/to/work/derived",
  "population": "EXAMPLE_COHORT",
  "pilot_receipt": "/abs/path/to/work/derived/pilot/BUILD_AUDIT.json",
  "pilot_receipt_sha256": "<fill in after the pilot finishes>",
  "max_loci": 100,
  "max_runtime_seconds": 1800,
  "sources": {
    "dkp_manifest": {"path": "evidence/dkp_manifest.json", "sha256": "<sha256>"},
    "dkp_database": {"path": "evidence/dkp.sqlite", "sha256": "<sha256>"},
    "dkp_reader": {"path": "evidence/dkp_reader.py", "sha256": "<sha256>"}
  }
}
```

The `sources` object must also list the other eight keys in the table above, in the same form. `max_loci` and `max_runtime_seconds` are optional; the values shown are the defaults.

- `allowed_output_root` must already exist, and `--out` must be inside it.
- Use absolute paths for `allowed_output_root` and `pilot_receipt`.
- Source `path` values may be absolute or relative to the config file.
- SQLite WAL, SHM or journal files beside a database are refused. Freeze the databases first.

## Run it

1. Run the pilot.

   ```sh
   python tools/build_enzyme_neighborhoods.py --config view-config.json --out /abs/path/to/work/derived/pilot --pilot
   ```

   The pilot needs five distinct owner candidates and adds one tested-no-call control when one exists.
2. On success it prints `{"status": "EXTRACTION_QC_PASS_CANDIDATE", ...}` and exits 0. The pilot folder holds `BUILD_AUDIT.json`.
3. Compute that file's SHA-256 and put it in `pilot_receipt_sha256`.
4. Run the full build into a new folder.

   ```sh
   python tools/build_enzyme_neighborhoods.py --config view-config.json --out /abs/path/to/work/derived/run001
   ```

   The full build includes every owner candidate plus up to five tested-no-call controls. It checks that the pilot receipt matches its hash, reads `PASS`, and was built from the same sources. It does not re-check the pilot's builder, template or control choices.
5. Open `run001/explorer.html` in a browser. It uses no network and no external assets.

Success looks like `explorer.html`, `BUILD_AUDIT.json` with `"status": "PASS"`, `CURRENT50_APPLICABILITY.json` and `SOURCE_MANIFEST.json` in the output folder. `SOURCE_MANIFEST.json` lists a hash for every other output file but not for itself; record its hash separately. `PASS` is a bounded software check: the exact census, architecture and gene rosters each have one row per gene key and the same key set, the parent join ran, and the evidence-index sidecars load. `BUILD_AUDIT.json` says this in `pass_scope`. It is not a complete reconciliation of annotations, function or flank context, and it does not mean current50 is complete.

## If the run stops

A hold prints `{"status": "HELD", "detail": ...}` and exits 2. Missing files print `MISSING_SOURCE` and unreadable JSON prints `PARSE_FAILED`; both also exit 2. Other unexpected errors are not caught and end the run with a Python traceback instead. A held or failed run never produces an empty "success".

Limits that cause a hold:

| Limit | Default | Config key |
|---|---|---|
| Selected loci | 100 | `max_loci` |
| Run time per invocation | 1,800 seconds | `max_runtime_seconds` |
| Gene plus context rows per locus | 2,500 | none |
| Feature rows per locus | 10,000 | none |
| Embedded view data | 32 MiB | none |

The locus cap is checked after the full source locus list is read. It is not a loading limit.

To recover:

1. Read `detail` for the cause.
2. For `RUNTIME_BUDGET_HOLD_RESUME_PARTITIONS`, run the same command again. Completed, hash-verified partitions are kept and the build resumes.
3. If you change a source file, the config, or any bound input, use a new output folder. Changed bindings or changed partition bytes hold the run.
4. A crash between a partition write and its receipt also leaves a hold. Keep the folder and ask for review before deleting anything.

The binding covers the selected source files, the builder file, the template and the selected loci. It does not cover every helper module the builder imports.

## How the view treats evidence

- Each locus is identified as `strain / full contig / region / BGC alias`. The identity is checked before anything is drawn.
- Genes join by locus tag, coordinates, strand and a normalized protein hash. Domain links need matching parent fields; a shared name is not a link.
- Duplicate DKP, census or exact-region architecture keys are refused (`DUPLICATE_GENE_HOLD`, `DUPLICATE_ARCHITECTURE_GENE_HOLD`), and their key sets must match the architecture key set.
- Coordinates are one-based and inclusive. A gap is the current start minus the previous displayed end minus one; a negative gap is an overlap. The first displayed gap is unknown. Each map has its own scale.
- Flank context contains only owner-term matches, so its gap values do not show adjacency.
- Domain states are: observed linked feature, tested with no linked feature, sparse-flank coverage unavailable, and unbound or ambiguous. A missing link is not domain absence.
- Recurrence counts three coordinate-ordered genes around a CDPS term match, once per locus per pattern, with orientation kept and the eligible-locus count shown. It does not show orthology, conservation, a shared pathway or a shared product. Tested-no-call loci sit outside that count.
- `BOUND` describes the source observation only. Channels without source data are left empty, not filled in.
- `scope` in `BUILD_AUDIT.json` states how many candidates and controls were actually selected. It says "no real no-call control" when there were none.

Integration, scientific review and release are separate decisions.
