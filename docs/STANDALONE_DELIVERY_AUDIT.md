# Standalone delivery audit

`tools/standalone_delivery_audit.py` checks that an HTML/SVG delivery folder or ZIP matches a file-and-hash list and loads nothing from outside it. It does not build a viewer or replace the producer, `handoff_gate.py`, `preflight_zip_hygiene.py`, figure provenance checks, or program/browser tests.

## Run

```sh
python3 tools/standalone_delivery_audit.py --root /path/to/delivery \
  --manifest /path/to/DELIVERY.json --receipt /outside/delivery/STATIC_QA.json
```

Use `--zip /path/to/delivery.zip` instead of `--root` to check a ZIP without extracting it. The receipt must use a new path outside a directory input and distinct from the input ZIP and manifest. Existing receipt paths are refused; exclusive creation also refuses a path created during the audit. No URL is fetched and no input file is modified. Requires Python 3.9 or newer; standard library only.

## Contract

```json
{
  "schema": "sapote.standalone_delivery.v1",
  "entrypoints": ["index.html"],
  "files": [
    {"path": "index.html", "bytes": 123, "sha256": "<actual lowercase SHA-256>"}
  ],
  "optional_provenance": [
    {
      "from": "index.html",
      "url": "file:///original/source/table.tsv",
      "reason": "Original evidence pointer; all required displayed data are embedded."
    }
  ]
}
```

The top-level manifest must be a JSON object, and each optional provenance reason must be a nonempty string. Malformed input produces a typed input-contract receipt.

Every manifest file needs its actual byte count and SHA-256; placeholders do not pass. Only listed files are checked; other files in the folder are ignored. A relative resource must exist, be inside the delivery root and belong to that roster. Hashes are recomputed from actual bytes. For a ZIP, member names must be canonical, relative, unique and non-symlink; extraction is never performed. Directory reads reject symlinks below the explicitly chosen root.

The checker reads exposed HTML/SVG resource attributes, inline style URLs, external CSS URLs/imports and HTML fragments. A local link to a missing file fails even if a same-named file exists outside the declared delivery. External runtime resources fail. Ordinary HTTP(S), mail and telephone anchors are reported as optional navigation and not fetched. An exact `optional_provenance` declaration for a relative, HTTP(S) or file URL with a reason can mark an anchor as an unavailable original-source pointer. It cannot exempt a script, stylesheet, image or other runtime resource; unused declarations fail.

## Interpret the receipt

`PASS_STATIC_CONTRACT` means that the checked syntax and exact listed bytes satisfy this small static contract. It is **not** an offline browser pass, a complete proof of all dependencies, a final page check, or permission to ship. `FAIL_STATIC_CONTRACT` identifies missing/escaping references, changed bytes or unsupported constructs needing review; it is not a biological no-hit. Input/schema errors return `FAIL_INPUT_CONTRACT`. Exit 0 is only the static-contract pass.

JavaScript is not executed, parsed semantically or sandboxed. Lexical words such as `fetch` are hints, including possible vendor dead code, not proof of a request. Dynamically generated URLs, JavaScript module graphs, embedded gzip/base64 payloads, service workers, Blob content, event handlers and browser API support require the producer's program checks and real browser testing. Duplicate HTML attributes, base tags, srcset, srcdoc, meta refresh and CSS-escaped URLs are explicit review holds rather than silently accepted syntax. Other markup behavior outside the stated parser remains outside scope. SVG is inspected for exposed resource references but is not visually rendered.

## Combine existing checks

1. Bind actual producer inputs and preserve complete BGC identity where applicable.
2. Build with the existing owner and run its data/program checks.
3. Run this static adapter on the exact delivery bytes and preserve its manifest and receipt.
4. Run the existing handoff gate and applicable ZIP/figure checks.
5. Inspect the actual final browser/PDF outputs, including selected structures and alignments. Bind those review records to the same final-byte hashes.

A change to final bytes invalidates the earlier static receipt for that output. Existing scientific, figure, identity and adoption holds remain visible after a packaging pass.
