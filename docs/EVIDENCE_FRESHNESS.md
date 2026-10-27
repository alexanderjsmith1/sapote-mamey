# Explicit-file evidence freshness

`tools/evidence_freshness.py` is an offline read-only adapter for retained SHA-256 pins and declared dependency edges. It does not discover a cohort or update a manifest. Use the existing input-manifest, availability, package-integrity and release-checking tools for their owning scopes.

## Manifest

```json
{
  "schema": "sapote-mamey.evidence-freshness.v1",
  "artifacts": [
    {
      "id": "gene_table",
      "path": "evidence/genes.tsv",
      "sha256": "",
      "unit": "artifact",
      "source_revision": "selected retained revision",
      "depends_on": []
    },
    {
      "id": "reader_report",
      "path": "report.md",
      "sha256": "",
      "unit": "artifact",
      "source_revision": "selected retained revision",
      "depends_on": ["gene_table"]
    }
  ]
}
```

Empty hashes deliberately produce `UNVERIFIED_BASELINE`; insert only the retained expected digest from the selected baseline. Paths resolve relative to the manifest; absolute paths are permitted local provenance. A symlink's resolved target is disclosed. Only regular files are hashed. Default budgets are 20,000,000 bytes per file and 100,000,000 total bytes; over-budget files remain unverified. A shared resolved path is hashed once in a run. Reuse requires the same observed file identity, size and nanosecond timestamps; a later different observation becomes `UNVERIFIED_CHANGED_SINCE_HASH`, not a cached match. An empty graph, duplicate IDs, unknown dependencies, cycles, malformed hashes, missing units or implicit dependency lists refuse input. Unit values are `artifact`, `locus`, `gene`, `strain`, `run` and `cohort`.

For locus/gene units, include `identity` with `strain`, `full_node`, `region` and `BGC_ID`, and select the owning bundle using `--bundle`. The adapter calls its existing `exact_locus_from_mapping`. Missing owner selection is an identity-verification hold. Missing/shortened/conflicting fields refuse the affected identity using that owner's rules. Do not derive any component from a filename or assume display validation proves canonical membership. A gene unit also needs a separately bound gene identity/sequence receipt before scientific use; the adapter does not invent one.

## States and interpretation

The direct states are `HASH_MATCH`, `CHANGED`, `MISSING_FILE`, `UNVERIFIED_BASELINE`, `UNREADABLE_FILE`, `NOT_REGULAR_FILE`, `UNVERIFIED_FILE_BUDGET`, `UNVERIFIED_TOTAL_BUDGET`, `UNVERIFIED_CHANGED_DURING_READ` and `UNVERIFIED_CHANGED_SINCE_HASH`. `HOLD_DIRECT` preserves that direct reason. `HOLD_METADATA` denotes a missing revision declaration or unresolved display-identity check. A directly matching artifact becomes `INVALIDATED_DEPENDENCY` when a declared ancestor is not current; all blocking ancestor IDs remain visible. Otherwise it becomes `CURRENT_BYTES`.

`CURRENT_BYTES` means the explicitly listed byte baseline matched under the implemented comparisons. It is not the Mode B freshness label `CURRENT`, a valid biological assignment, a true no-hit, proof of actual producer consumption or scientific adoption. Revision labels are declarations; bind the owning revision files as dependencies if their bytes matter. A manifest does not validate itself: its trust must come from a separately selected source or receipt.

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/evidence_freshness.py retained_manifest.json \
  --bundle /absolute/path/to/selected/bundle > current_recheck.json
```

Exit 0 means all listed checks passed; 1 means typed holds; 2 means invalid input. Keep the actual receipt and baseline separately. Investigate changed or missing sources before rebuilding an affected report. Do not rewrite the baseline to turn a hold green. Keep scientific holds even when every byte matches. This check does not supply rendered-page review, sequence equality, gene roster completeness, alignment coverage, taxonomy, compound identity, activity, release authority or publication acceptance.

Artifact reads are bounded by the remaining per-file and total byte budgets, including a file that grows after its size precheck. Descriptor size/identity are checked before accepting a complete digest. `hashed_bytes` counts actual payload bytes consumed, including discarded attempts; each row reports `read_bytes`. Cached unchanged aliases read no additional payload. Manifest and optional identity-owner code reads are outside those artifact-payload counters. API budgets, like CLI budgets, must be positive integers.
