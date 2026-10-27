# Patch packet policy

A patch packet is a portable implementation delta, not an analysis workspace.

It may contain implementation files, tests, schemas, generic documentation, a unified diff, and compact hash-bound receipts. It must not contain sequencing reads, assemblies, alignments, reassembly outputs, scientific result trees, software environments, package caches, copied release baselines, or generated caches.

Before owner review, and again immediately before cut selection, check the selected packet:

```bash
python tools/patch_packet_preflight.py '/path/to/packet' \
  --out '/path/to/existing-review-folder/packet-preflight.json'
```

Choose a fresh report path outside the packet. Defaults are 25 MiB per packet and 10 MiB per file. Exit 0 means no implemented packet finding; exit 3 reports findings that must be resolved before cut selection. Keep the saved report with the reviewed packet hash and actual exit status.

Scientific evidence belongs in a separately governed evidence root and is referenced by immutable receipt/hash. Reusable tools belong in a shared tooling root with an environment manifest. The exact sealed baseline is identified by artifact hash; the patch carries a unified diff rather than a copy of the baseline.

Passing this mechanical gate does not accept, integrate, seal, release, or scientifically validate a patch.

## What the preflight establishes

The preflight enumerates files and apparent/allocated bytes, checks configured forbidden directory components and size limits, requires top-level `PATCH_CARD.md`, admits a diff or `candidate_files` tree, and detects a copied baseline only through a paired marker-file heuristic. Diff inspection flags selected forbidden logical payload paths and plain binary-diff markers. It does not apply the delta, compare its target baseline/hash, run tests, inspect all scientific content or prove every path/symlink stays within the packet. Independently review provenance and actual content rather than treating a PASS as universal containment/privacy clearance.

The `--max-total-mb` and `--max-file-mb` options override the default MiB limits; size checks use apparent file bytes. `--out` writes directly to the selected path without a backup guard, so preserve any prior unique receipt. If you omit `--out`, the result is printed rather than saved.

Packet preflight and [lane structure checks](PATCH_WORKSPACE_LAYOUT.md) are separate. A directory of staged Markdown can be a review candidate without already being a cut-ready implementation lane. Keep source evidence in place with exact path+SHA-256; isolate modified files and compact evidence receipts only. No source-evidence overwrite, package copy or release action follows from this policy. Retain executed validation and any authorized patch application in separate receipts.
