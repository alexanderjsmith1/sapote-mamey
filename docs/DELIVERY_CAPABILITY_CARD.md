# Delivery Capability Card — candidate

Use this card when you hand over an HTML viewer: it records which browser features the viewer needs, the exact bytes delivered, and which checks were run on those bytes. It does not measure browser compatibility, execute JavaScript, redraw figures, validate biology or authorize adoption. Existing viewer builders and check producers remain the owners of their outputs.

## Command and files

```sh
python3 tools/delivery_capability_card.py --config /path/to/config.json \
  --json-out /path/to/candidate_card.json --html-out /path/to/candidate_card.html
```

Requires Python 3.9+ and the standard library only. Input paths are relative to the config location or absolute. Inputs are read in place; no artifact is copied. Outputs must be distinct from every selected input and cannot be symlinks. Changed existing derived outputs require `--replace-candidate`; byte-identical replay is allowed. Each output replacement is atomic, but JSON and HTML are not a transactional pair after interruption. Keep both current output hashes in a delivery manifest.

Exit 0 means the configured artifact's exact bytes were found and the card was produced; **it does not mean all checks passed**. Inspect the card's states and holds. Exit 1 means the artifact is missing or differs from the config. Invalid input raises an error rather than generating a passing card. No network or browser is used.

## Configuration

```json
{
  "schema": "sapote.delivery_capability_card.v1",
  "artifact": {"path": "/path/to/viewer.html", "bytes": 123, "sha256": "<actual SHA-256>"},
  "declared_capabilities": [
    {
      "name": "DecompressionStream", "requirement": "REQUIRED",
      "evidence": {
        "path": "/path/to/producer.md", "sha256": "<actual SHA-256>",
        "excerpt": "<exact producer requirement text>"
      }
    },
    {"name": "WebGL", "requirement": "NOT_DECLARED", "reason": "No reviewed producer declaration supplied."}
  ],
  "checks": [
    {
      "kind": "program_behavior", "adapter": "delivery_check_v1",
      "path": "/path/to/producer_receipt.json", "sha256": "<actual receipt SHA-256>"
    }
  ]
}
```

Placeholders do not pass. Required/optional capability declarations need a pinned actual source and exact excerpt. This verifies the supplied source text, not whether its scientific or compatibility assertion is true. Requirements may be `REQUIRED`, `OPTIONAL` or `NOT_DECLARED`; absence of a declaration must not become optional support or a measured failure. Names are not silently inferred from vendor code or filenames. Unknown browser needs can remain unknown.

Each check kind appears at most once: `static_dependencies`, `data_syntax`, `program_behavior`, `browser_compatibility`, `visual_review`. The selected receipt itself must be SHA-256 pinned. Receipt bytes are read once for hashing/parsing. The card does not invoke receipt producers or synthesize missing producer results.

## Proposed producer receipt contract

```json
{
  "schema": "sapote.delivery_check.v1",
  "kind": "program_behavior",
  "artifact": {"sha256": "<actual final artifact SHA-256>", "bytes": 123},
  "result": "PASS",
  "method": "<actual producer/tool and version>",
  "scope": "<what was actually checked and important limits>",
  "checked_at": "2026-10-24T12:00:00-07:00",
  "environment": {"browser": "<if measured>", "browser_version": "<if measured>", "os": "<if measured>"}
}
```

Results may be `PASS`, `FAIL`, `NOT_PERFORMED` or `HELD`. A browser-compatibility PASS additionally needs a timezone-qualified ISO timestamp and nonblank browser/version/OS fields. It remains a bound producer assertion limited to that environment. An API requirement, program-harness PASS or static inspection must never be relabeled as browser compatibility. A receipt hash does not authenticate a reviewer, prove a tool ran, or grant release authority.

## Existing receipt adapters and boundaries

- `tb03_static`: TB03 schema plus an exact configured `member` in `files_checked`; static status, member state, hash, bytes and empty errors are checked. It cannot create a program/browser pass.
- `locus_data_syntax`: retained locus QA's named data/syntax status, `HTML_sha256`, byte count and errors. Its original `limits` stay visible.
- `protein_data_syntax`: retained point-preservation/syntax status and `output_viewer_sha256`; source says point arrays unchanged. This is a hash-only legacy binding, not a browser check.
- `unbound_legacy`: preserves a selected historical receipt as `RECEIPT_UNBOUND`. It never borrows a hash from a neighboring QA file to make an unbound program result pass.
- `report_visual`: retained `RENDERED_PAGES_INSPECTED` receipt only for exact target PDF hashes in `reviewed_PDFs`. Report inspection cannot establish HTML visual acceptance.
- `delivery_check_v1`: the proposed typed producer contract above.

For `tb03_static` and `locus_data_syntax`, the receipt byte count is required and must be a nonnegative integer. Missing/null counts and booleans are invalid receipts; these adapters cannot silently become hash-only bindings. The explicitly hash-only legacy adapters retain their stated scope.

## States

`NOT_PERFORMED` means no receipt was selected for that kind. `RECEIPT_MISSING` means a named input is unavailable. `RECEIPT_REVISION_NOT_PINNED`, `RECEIPT_HASH_MISMATCH` and `RECEIPT_INVALID` describe unresolved receipt provenance. `RECEIPT_UNBOUND` means the selected receipt does not establish an admitted exact-target binding. `RECEIPT_STALE_FOR_TARGET` means its target hash or byte count differs. `RECEIPT_SCOPE_MISMATCH` means another check kind/artifact is being offered, for example PDF inspection for HTML. `ARTIFACT_BINDING_HOLD` prevents a historical pass from being reused when the configured delivery changed. `BOUND_REPORTED_*` preserves a result only for matching artifact bytes, without upgrading its scope.

Freshness here is content binding, not a time-to-live. Even exact old HTML bytes may behave differently in another browser or OS. A declaration source change invalidates its source binding; a target-byte change invalidates the target binding. A changed receipt invalidates its pin. Missing, unperformed, invalid and reported-failed states remain distinct.

Use the existing producer checks and TB03 static adapter before final page inspection. Bind the actual final-browser/visual check to the exact bytes afterward. Keep scientific, identity, figure and adoption holds outside packaging acceptance.
