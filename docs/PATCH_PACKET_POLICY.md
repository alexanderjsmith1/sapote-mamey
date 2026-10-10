# Patch packet policy

A patch packet is a portable implementation delta, not an analysis workspace.

It may contain implementation files, tests, schemas, generic documentation, a unified diff, and compact hash-bound receipts. It must not contain sequencing reads, assemblies, alignments, reassembly outputs, scientific result trees, software environments, package caches, copied release baselines, or generated caches.

Run `python tools/patch_packet_preflight.py PATCH_PACKET` before owner review and immediately before cut selection. The default hard limits are 25 MB per packet and 10 MB per file. Exit code 3 means the packet is not cut-selectable.

Scientific evidence belongs in a separately governed evidence root and is referenced by immutable receipt/hash. Reusable tools belong in a shared tooling root with an environment manifest. The exact sealed baseline is identified by artifact hash; the patch carries a unified diff rather than a copy of the baseline.

Passing this mechanical gate does not accept, integrate, seal, release, or scientifically validate a patch.

## What the preflight establishes

`tools/patch_packet_preflight.py:87–143` enumerates files and apparent/allocated bytes, checks configured forbidden directory components and size limits, requires top-level `PATCH_CARD.md`, admits a diff or `candidate_files` tree, and detects a copied baseline only through a paired marker-file heuristic. Diff inspection flags selected forbidden logical payload paths and plain binary-diff markers (`:43–84`). It does not apply the delta, compare its target baseline/hash, run tests, inspect all scientific content or prove every path/symlink stays within the packet. Independently review provenance and actual content rather than treating a PASS as universal containment/privacy clearance.

Default limits are 25 and 10 **MiB** (arguments labeled MB are multiplied by 1024²), measured as apparent file bytes; they can be overridden by CLI options. Optional `--out` directly writes its report path without a fresh-output/backup guard (`:146–176`). Preserve any prior unique receipt and choose a permitted fresh report path. No report is written unless that option is selected; normal printing is not a saved receipt.

Packet preflight and [lane structure checks](PATCH_WORKSPACE_LAYOUT.md) are separate. A directory of staged Markdown can be a review candidate without already being a cut-ready implementation lane. Keep source evidence in place with exact path+SHA-256; isolate modified files and compact evidence receipts only. No source-evidence overwrite, package copy or release action follows from this policy. Retain executed validation and any authorized patch application in separate receipts.
