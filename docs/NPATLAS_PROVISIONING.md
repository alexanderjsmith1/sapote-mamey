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
# Activate the bundle Python environment and run from the bundle root.
export MAMEY_NPATLAS_DIR="/absolute/path/to/writable/npatlas_data"
python tools/npatlas_provision.py doctor
python tools/npatlas_provision.py inspect --source /path/to/np_atlas_v2024_09.json
python tools/npatlas_provision.py provision \
    --source /path/to/np_atlas_v2024_09.json \
    --out "$MAMEY_NPATLAS_DIR/all_actinobacteria_npatlas_ref.json" \
    --dataset-version v2024_09 --normalize \
    --phylum Actinobacteria --phylum Actinomycetota
```

- **Consumer schema and layout.** Raw v2024_09 records need `--normalize` to map
  `original_name`/`origin_reference`/classifier result keys to the consumer's fields before
  filtering and writing. The phylum allowlist above uses a derived scalar from the source taxonomy;
  repeated `--phylum` values are ORed and imply normalization. For a genus-specific normalized
  subset, use `--genus-field origin_organism.genus --genus Streptomyces`. The flat defaults
  `origin_type`, `origin_taxon` and `genus` belong to a different schema and must not be assumed
  for raw or normalized v2024_09 records.
- **Discoverable add-ons.** The consumer searches `all_actinobacteria_npatlas_ref.json` and
  `bacteria_nonactino_npatlas_ref.json` inside the configured directory. An arbitrary `--out`
  filename is valid as a standalone subset, but is not automatically loaded. Keep its actual
  filter and included/excluded counts in the receipt; a filename does not establish complete
  taxonomic coverage. Provisioning a file is not scientific acceptance of its references.
- **Input streaming and memory.** The historical official JSON download is approximately 475 MB; measure your selected release. `inspect`/`provision` read its records with
  `ijson` (system install if present, else the vendored copy at `mamey/_vendor/ijson` — same
  dual-name fallback pattern as `mamey/antismash_evidence.py`) — the file is never
  `json.loads`-ed whole at input. However, `provision` retains every selected record in a Python list and serializes the complete output in memory; a broad or empty filter can consume substantial memory. The downstream resolver also reads each discovered subset whole. Input streaming is not a bounded-memory guarantee for this workflow. A plain-text `.sdf` source streams its declared property blocks the same
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
- **`inspect`** leaves the source unchanged and reports hash, byte count, record count and
  sampled keys. By default it writes the report only to stdout; `--out-json <report.json>`
  additionally persists that report to the selected path.
- **`doctor`** reports whether `ijson` is available (and from where) and whether `rdkit` is
  importable, plus the NP Atlas dataset's own provisioning status via `mamey.external_data`. The CLI returns 0 for this report even when a dependency or dataset is unavailable; inspect the reported states before proceeding.

## Outputs, recovery and consumer limits

Before provisioning, use distinct resolved paths for the source, subset, inspect report and receipt. The library does not refuse a source/output alias: `--out` pointing to the source can replace that source after reading it. The CLI's report/receipt paths must also be kept distinct from source and subset. Preserve source evidence and write the candidate subset to a fresh path; existing destinations can be overwritten.

The subset uses a fixed sibling `<out>.tmp` and `os.replace`; this publishes one file, not an atomic subset-plus-receipt transaction. Concurrent writers can collide at that fixed temporary path. A failed receipt write may leave the subset already published. Check exact destination paths and hashes before a retry; do not delete source evidence or blindly rerun into an existing directory. Library output parents are created, but explicitly create the report/receipt parent directories before the CLI's atomic writer is used.

An empty clause list selects all emitted dictionary records. Repeated phylum/genus values are allowlists; separate taxon-substring clauses are ANDed. Non-dictionary JSON entries are skipped. An incorrect JSON root can yield zero records without a refusal; `provision` can successfully write `{"compounds": []}`. Inspect the actual root, record count, normalized field names and selected count before accepting the subset. A successful write is not proof that the intended population was selected. `inspect` makes a full counting pass, and its stdout/report contains sampled records as well as keys; review those contents before sharing it.

The resolver discovers two named files across the configured directory and fallback locations; setting `MAMEY_NPATLAS_DIR` prioritizes a directory rather than restricting loading to it. It combines readable files, uses the first record for each lowercased name and caches its index. Changing environment variables or replacing files in an already running process does not automatically refresh that cache; start a fresh process after changing provisioned references. The resolver does not automatically reopen provisioning receipts or verify their hashes. Record which files contributed, retain their hashes and inspect duplicate-name/source conflicts separately. Availability means a nonempty loaded index, not accepted identity, provenance or scientific completeness.

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
