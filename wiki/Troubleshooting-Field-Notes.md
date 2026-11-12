# Troubleshooting field notes — real failures, real fixes

Use historical failure observations as diagnostic leads.  
This page is for operators investigating a problem.

These are dated project observations, not a guarantee about current external programs, operating
systems, service limits or every installation. Start with [current recovery guidance](Common-Mistakes.md)
and the actual command/input receipt. Preserve evidence before repair; a historical fix is a
diagnostic possibility, not permission to rerun, download, replace references or change security policy.

## Unquoted paths can break shell-out tools

The recorded failure involved a wrapper constructing unquoted shell paths. Test the selected executable and wrapper rather than assuming every tool fails under paths containing spaces — often with misleading errors ("Incorrect number of
command line arguments" from cmsearch via barrnap). **Fix:** stage inputs, databases,
and outputs in a space-free work dir (`/tmp/...`), run there, copy results back. Wrapper scripts
should enforce this (the fungal-toolchain barrnap wrapper lives in the phylo workspace, outside this bundle).

## macOS Gatekeeper quarantines downloaded scientific binaries

A historical unsigned-binary launch produced a quarantine dialog. Verify the exact binary's
source, integrity, platform compatibility and the host's approved launch policy before remediation.
Do not treat an official-site URL alone as verification or recursively clear quarantine across a
directory by default. Record a missing/deferred capability when execution is not approved.

## Architecture mismatches on Apple Silicon

A Linux wheel or binary is not a native macOS-arm64 build. The recorded
Biopython-wheel and BUSCO-environment failures concern specific artifacts; inspect
the selected release, platform tags and dependencies rather than generalizing
that every BUSCO installation fails on arm64.
**Fix:** fetch a platform-matched build or run in the Linux container. Switching tools, for
example from BUSCO to compleasm, is a method choice to review, not a repair: compleasm has its own
executable and lineage-data requirements, and its outputs are not interchangeable with BUSCO's. Check the actual format and architecture with `file /path/to/executable`,
including universal builds, against the chosen execution environment.

## A "failed" conda env may still have delivered usable binaries

A historical environment-creation failure left some binaries on disk — the broken BUSCO env
still provided working `miniprot`, `hmmsearch`, and `diamond`. **Check:** inventory existing executable paths, versions and imports. A leftover binary does not prove a coherent usable environment; do not adopt a partially installed environment solely because one file exists.

## conda itself can break (`env: python: No such file or directory`)

The `conda` entry script's `#!/usr/bin/env python` shebang fails when no bare `python` is on PATH.
If the selected conda entry point is a Python script, inspect its shebang and
use the matching existing interpreter with that script and real arguments. Do not
assume a particular installation prefix or adopt a damaged environment blindly.

## NCBI eutils rate-limiting looks like "no results"

A historical marker-fetch sequence returned unexpectedly empty responses after rapid requests.
An empty response can have several causes; inspect HTTP status, service errors, query syntax,
accession/version and retry metadata before calling it absence. Use the selected current runner's
authorized pacing/backoff and upstream service requirements. The old observed count is not a
current quota, and another client is not an automatic exemption from service limits.

## Tools that fetch their databases at runtime

Database readiness is separate from executable installation and varies with the selected release. The old Barrnap ≥1.10 database/download observations were recorded for a particular environment, not verified for every installation. Inspect the installed version/help and database inventory before any separately authorized download. Avoid copying a whole database or source tree as a default repair; keep original evidence in place and isolate only changed files. See [Barrnap version and integration scope](../docs/BARRNAP.md).

## Skipped tests are unevaluated cases

Some live/reference tests skip when their declared prerequisites are absent.
Read and retain the skip reason, then determine whether the intended task requires
that case to run. A skip is neither a pass nor proof of a defect. Preserve the test
and its unresolved coverage rather than silently waiving it.

## Version drift survives sealing

Doc headers and version literals that are not machine-owned drift silently across cuts (see
[Versioning](Versioning.md) for a retained comment about earlier index freezes).
**Fix:** `tools/sync_version.py` owns a declared set of current version surfaces, not every version literal. Inspect its exact anchors and use the corresponding checks during an authorized bump. Preserve producing versions and dated review/run stamps; synchronization does not revalidate their historical content.

## One bad reference record can fail a whole tree

A mis-deposited reference record can cause a tree sanity gate to fail. **Check:** verify reference identity, alignment, model and record provenance. Exclude only with a documented source-backed reason and record the altered denominator; do not weaken the gate to hide a failure. And distinguish that case from a genuinely divergent *query*, where the gate FAIL is a quality-control observation requiring interpretation, not proof of novelty: report numbers, withhold the figure.

## IQ-TREE outgroup crash

A recorded IQ-TREE/outgroup/partition combination aborted in `setRootNode`.
Check the selected version, input and failure log before assuming the same cause.
An unrooted analysis followed by explicit rooting is a method change requiring
review of the model, outgroup and resulting tree; it is not an automatic repair
or permission to bypass the shared gate.

*General habit behind all of these: verify before asserting — check the actual binary, env, file,
or record before concluding a tool "doesn't work" or data "doesn't exist."*
