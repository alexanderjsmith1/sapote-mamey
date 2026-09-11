# NP Atlas provisioning (user-supplied, never redistributed)

**Modules:** `mamey/npatlas_provision.py` (library) + `tools/npatlas_provision.py` (operator front
door) + `tests/test_npatlas_provision_v97405.py` + `tests/test_npatlas_env_unification_v97405.py`.
Structure rendering lives in `mamey/npatlas_structure.py::render_structure_svg`.

Use a locally downloaded NP Atlas dataset for provisioning and structure display.

## Dataset configuration

Set `MAMEY_NPATLAS_DIR` to the dataset directory. `SM_NPATLAS_DIR` is a deprecated
compatibility alias; when both are set, `MAMEY_NPATLAS_DIR` takes precedence.
Provisioning receipts record the dataset license from the bundled external-data registry.
Check the terms for the dataset version you download before use. The provisioning tool
consumes a user-supplied source and writes the requested subset locally; the bundle does
not redistribute the NP Atlas dataset.

## `npatlas provision` (NPA-03, NPA-04)

```bash
Tools/bin/python3 tools/npatlas_provision.py doctor
Tools/bin/python3 tools/npatlas_provision.py inspect --source /path/to/np_atlas_v2024_09.json
Tools/bin/python3 tools/npatlas_provision.py provision \
    --source /path/to/np_atlas_v2024_09.json \
    --out ./my_npatlas_actino_subset.json \
    --dataset-version v2024_09 \
    --origin-type bacterium --taxon-contains Streptomyces
```

- **Streaming.** The official JSON download is ~475 MB. `inspect`/`provision` stream it with
  `ijson` (system install if present, else the vendored copy at `mamey/_vendor/ijson` — same
  dual-name fallback pattern as `mamey/antismash_evidence.py`) — the file is never
  `json.loads`-ed whole. A plain-text `.sdf` source streams its declared property blocks the same
  way, with no chemistry-toolkit dependency for provisioning (RDKit is only needed for the
  separate structure-*rendering* path below).
- **Root-shape auto-detection.** A bare top-level JSON array (the official download's shape) is
  read at ijson prefix `item`; a `{"compounds": [...]}` wrapper (this bundle's own filtered add-on
  file shape, see `mamey/npatlas_resolver.py::_REF_FILES`) is read at `compounds.item`. Override
  with `--json-root` if a source uses neither.
- **Declarative filter, never executed code.** `--origin-type` (repeatable), `--taxon-contains`
  (repeatable, case-insensitive substring on `--taxon-field`, default `origin_taxon`), `--genus`
  (repeatable allowlist), and `--predicate-file` (a JSON **list** of
  `{"field", "op", "value"}` clauses, `op` one of `eq`/`in`/`contains`/`icontains`, dotted `field`
  paths) — all ANDed together. A predicate file is data, not a script: "a portable LLM may help
  author or inspect a filter specification, but deterministic code performs the actual row
  selection" (audit doc's recommended contract). No predicate is ever `exec`'d.
- **Content-addressed receipt.** `provision` writes the filtered subset to `--out` and prints a
  receipt with: `source_path`, `source_sha256`, `source_bytes`, `dataset_version` (operator-typed,
  e.g. `v2024_09` — this module cannot infer it from the file), `licence_id`/`licence_text`,
  `filter_rule` (the exact clauses applied), `included_count`, `excluded_count`, `output_path`,
  `output_sha256`, `tool_version`, `claim_ceiling`. `--format tsv` prints one row instead;
  `--out-receipt` also writes the receipt to a file.
- **`inspect`** is read-only — hash, byte count, total record count, and a small sample of the
  first records' keys, for previewing a source before committing to a filter. Never writes
  anything.
- **`doctor`** reports whether `ijson` is available (and from where) and whether `rdkit` is
  importable, plus the NP Atlas dataset's own provisioning status via `mamey.external_data`.

## Structure rendering (NPA-03 — `mamey/npatlas_structure.py::render_structure_svg`)

Deterministic RDKit `MolDraw2D` SVG rendering of a **bound reference structure only** — not a
predicted BGC product. Every result, whatever its state, carries the mandatory caption:

> structure of a related characterized reference, not the predicted BGC product

States:

| State | When |
|---|---|
| `RENDERED` | RDKit parsed a real, specific, non-wildcard SMILES; `svg` holds the drawing. |
| `HOLD` | No SMILES, a wildcard/R-group SMILES (`*`, `R1`, …), or RDKit could not parse it. Never a placeholder or guessed structure. |
| `UNAVAILABLE` | `rdkit` does not import in this environment. Not an error — provisioning and every other module here works fully without RDKit; only rendering needs it. |

`svg` is `None` for every state except `RENDERED`. Rendering is deterministic given the same
SMILES and RDKit version (no seeded randomness in `Compute2DCoords`/`MolDraw2D`).

## Scope limitations

- **No Tanimoto comparison** (audit NPA-05) — a similarity score against a partial/wildcard
  prediction could read as identity; gating that correctly is a separate, owner-approved cut.
- **No ChemSpider link-out/enrichment** (audit NPA-06) — a live third-party service with its own
  terms; kept optional and owner-gated, not built here.
- **No redistribution of NP Atlas data.** Every fixture in the test suite is synthetic
  (`SYN-###`-style fake NPAIDs/names); the real local NP Atlas copy referenced by the audit's own
  `SOURCE_BINDINGS.tsv` is for a manual operator smoke test only, never assumed as a default path.

## Claim ceiling

Provisioning receipts report record counts, hashes, and filter rules only — never a
taxonomic-distribution, bioactivity, structure-similarity, or BGC-identity claim. Structure
rendering shows the structure of a related characterized reference, never the predicted product of
a BGC. See `docs/EXTERNAL_DATA.md` for the full third-party-dataset provisioning contract this
module follows.
