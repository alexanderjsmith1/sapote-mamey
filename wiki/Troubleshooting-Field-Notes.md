# Troubleshooting field notes — real failures, real fixes

Every entry here was hit for real in operating this project (dates given). Check this page before
debugging from scratch — the failure modes recur.

## Paths with spaces break shell-out tools (HARD RULE)

BLAST+, barrnap 1.10.x, and anything that builds shell commands from unquoted paths will fail
under directories whose names contain spaces — often with misleading errors ("Incorrect number of
command line arguments" from cmsearch via barrnap, 2026-09-01). **Fix:** stage inputs, databases,
and outputs in a space-free work dir (`/tmp/...`), run there, copy results back. Wrapper scripts
should enforce this (the fungal-toolchain barrnap wrapper lives in the phylo workspace, outside this bundle).

## macOS Gatekeeper quarantines downloaded scientific binaries

First run of an unsigned binary from the internet (Infernal, etc.) triggers a "cannot be verified"
dialog that offers to move it to the trash — and deleting one binary from a toolset breaks it
(cmsearch, 2026-09-01). **Fix:** never delete; clear the flag with
`xattr -dr com.apple.quarantine <binaries-dir>` and re-extract any binary already removed. Official
tarballs from the tool author's site are the trusted source.

## Architecture mismatches on Apple Silicon

Linux/x86_64 wheels and binaries do not install/run on macOS-arm64 (the bundled `biopython`
cp312/manylinux wheel; BUSCO's metaeuk/augustus conda stack, which fails outright on arm64).
**Fix:** fetch a platform-matched build, use a pure-Python alternative (compleasm instead of
BUSCO), or run in the Linux container. Check `file <binary>` says `arm64` before debugging deeper.

## A "failed" conda env may still have delivered usable binaries

A conda create that errors on one package often installed the rest first — the broken BUSCO env
still provided working `miniprot`, `hmmsearch`, and `diamond` (2026-09-01). **Fix:** before
re-installing a dependency, look inside existing envs (`ls miniconda3/envs/*/bin/<tool>`).

## conda itself can break (`env: python: No such file or directory`)

The `conda` entry script's `#!/usr/bin/env python` shebang fails when no bare `python` is on PATH.
**Fix:** invoke it explicitly: `miniconda3/bin/python miniconda3/bin/conda <subcommand> ...`.

## NCBI eutils rate-limiting looks like "no results"

After ~10 rapid esearch/efetch calls, queries silently return 0 hits rather than an error
(observed mid-marker-fetch, 2026-09-01). **Fix:** treat a sudden empty result after many calls as
throttling, not absence; add sleeps and a retry loop; for genomes use the `datasets` CLI (not
throttled the same way). Never put an email/identity into API requests.

## Tools that fetch their databases at runtime

Newer releases increasingly ship without local databases (barrnap ≥1.10 carries only its diamond
mRNA db; compleasm downloads lineage files on demand). A tool that "installed fine" can still fail
on first run wanting a download — and its bulk updater may be huge (barrnap's `--updatedb` pulls
the full Rfam + Swiss-Prot). **Fix:** fetch only what the run needs (e.g. the three Rfam rRNA
family CMs, ~3.5 MB, then `cmpress`), and record the build provenance next to the db.

## Skipped tests are gates, not breakage

A block of `*_live` / reference-panel tests SKIP by design — they need local antiSMASH ZIPs that
are not shipped. **Skips mean "gated," not "broken."** Do not chase them; do not delete them.

## Version drift survives sealing

Doc headers and version literals that are not machine-owned drift silently across cuts (see
[Versioning](Versioning.md) for the three documented freezes of `CURRENT_DOCS_INDEX.md`).
**Fix:** `tools/sync_version.py` owns every stamp; run it plus the version tests at every bump.

## One bad reference record can fail a whole tree

A single mis-deposited GenBank record (a 5.4-subs/site terminal branch in a 36-taxon LSU tree,
2026-09-01) trips the sanity gate for the entire figure. **Fix:** drop the record and rebuild —
never loosen the gate. And distinguish that case from a genuinely divergent *query*, where the
gate FAIL is itself the scientific finding: report numbers, withhold the figure.

## IQ-TREE outgroup crash

`iqtree -o <outgroup>` combined with partition models can abort (SIGABRT in setRootNode,
2026-09-01). **Fix:** build unrooted, then root afterwards (Bio.Phylo `root_with_outgroup`) before
rendering.

*General habit behind all of these: verify before asserting — check the actual binary, env, file,
or record before concluding a tool "doesn't work" or data "doesn't exist."*
