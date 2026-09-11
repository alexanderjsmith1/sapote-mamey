# Patch packet policy

A patch packet is a portable implementation delta, not an analysis workspace.

It may contain implementation files, tests, schemas, generic documentation, a unified diff, and compact hash-bound receipts. It must not contain sequencing reads, assemblies, alignments, reassembly outputs, scientific result trees, software environments, package caches, copied release baselines, or generated caches.

Run `python tools/patch_packet_preflight.py PATCH_PACKET` before owner review and immediately before cut selection. The default hard limits are 25 MB per packet and 10 MB per file. Exit code 3 means the packet is not cut-selectable.

Scientific evidence belongs in a separately governed evidence root and is referenced by immutable receipt/hash. Reusable tools belong in a shared tooling root with an environment manifest. The exact sealed baseline is identified by artifact hash; the patch carries a unified diff rather than a copy of the baseline.

Passing this mechanical gate does not accept, integrate, seal, release, or scientifically validate a patch.
