# Troubleshooting field notes — real failures, real fixes

These are dated project observations, not a guarantee about current external programs, operating
systems, service limits or every installation. Start with [current recovery guidance](Common-Mistakes.md)
and the actual command/input receipt. Preserve evidence before repair; a historical fix is a
diagnostic possibility, not permission to rerun, download, replace references or change security policy.

## Unquoted paths can break shell-out tools

The recorded failure involved a wrapper constructing unquoted shell paths. Test the selected executable and wrapper rather than assuming every tool fails under paths containing spaces — often with misleading errors ("Incorrect number of
command line arguments" from cmsearch via barrnap, 2026-09-01). **Fix:** stage inputs, databases,
and outputs in a space-free work dir (`/tmp/...`), run there, copy results back. Wrapper scripts
should enforce this (the fungal-toolchain barrnap wrapper lives in the phylo workspace, outside this bundle).

## macOS Gatekeeper quarantines downloaded scientific binaries

A historical unsigned-binary launch produced a quarantine dialog. Verify the exact binary's
source, integrity, platform compatibility and the host's approved launch policy before remediation.
Do not treat an official-site URL alone as verification or recursively clear quarantine across a
directory by default. Record a missing/deferred capability when execution is not approved.

## Architecture mismatches on Apple Silicon

Linux/x86_64 wheels and binaries do not install/run on macOS-arm64 (the bundled `biopython`
cp312/manylinux wheel; BUSCO's metaeuk/augustus conda stack, which fails outright on arm64).
**Fix:** fetch a platform-matched build, use a pure-Python alternative (compleasm instead of
BUSCO), or run in the Linux container. Check `file <binary>` says `arm64` before debugging deeper.

## A "failed" conda env may still have delivered usable binaries

A historical environment-creation failure left some binaries on disk — the broken BUSCO env
still provided working `miniprot`, `hmmsearch`, and `diamond` (2026-09-01). **Check:** inventory existing executable paths, versions and imports. A leftover binary does not prove a coherent usable environment; do not adopt a partially installed environment solely because one file exists.

## conda itself can break (`env: python: No such file or directory`)

The `conda` entry script's `#!/usr/bin/env python` shebang fails when no bare `python` is on PATH.
**Fix:** invoke it explicitly: `miniconda3/bin/python miniconda3/bin/conda <subcommand> ...`.

## NCBI eutils rate-limiting looks like "no results"

A historical marker-fetch sequence returned unexpectedly empty responses after rapid requests.
An empty response can have several causes; inspect HTTP status, service errors, query syntax,
accession/version and retry metadata before calling it absence. Use the selected current runner's
authorized pacing/backoff and upstream service requirements. The old observed count is not a
current quota, and another client is not an automatic exemption from service limits.

## Tools that fetch their databases at runtime

Database readiness is separate from executable installation and varies with the selected release. The old Barrnap ≥1.10 database/download observations were recorded for a particular environment, not verified for every installation. Inspect the installed version/help and database inventory before any separately authorized download. Avoid copying a whole database or source tree as a default repair; keep original evidence in place and isolate only changed files. See [Barrnap version and integration scope](../docs/BARRNAP.md).

## Skipped tests are gates, not breakage

A block of `*_live` / reference-panel tests SKIP by design — they need local antiSMASH ZIPs that
are not shipped. **Skips mean "gated," not "broken."** Do not chase them; do not delete them.

## Version drift survives sealing

Doc headers and version literals that are not machine-owned drift silently across cuts (see
[Versioning](Versioning.md) for the three documented freezes of `CURRENT_DOCS_INDEX.md`).
**Fix:** `tools/sync_version.py` owns every stamp; run it plus the version tests at every bump.

## One bad reference record can fail a whole tree

A single mis-deposited GenBank record (a 5.4-subs/site terminal branch in a 36-taxon LSU tree,
2026-09-01) trips the sanity gate for the entire figure. **Check:** verify reference identity, alignment, model and record provenance. Exclude only with a documented source-backed reason and record the altered denominator; do not weaken the gate to hide a failure. And distinguish that case from a genuinely divergent *query*, where the gate FAIL is a quality-control observation requiring interpretation, not proof of novelty: report numbers, withhold the figure.

## IQ-TREE outgroup crash

`iqtree -o <outgroup>` combined with partition models can abort (SIGABRT in setRootNode,
2026-09-01). **Fix:** build unrooted, then root afterwards (Bio.Phylo `root_with_outgroup`) before
rendering.

*General habit behind all of these: verify before asserting — check the actual binary, env, file,
or record before concluding a tool "doesn't work" or data "doesn't exist."*
