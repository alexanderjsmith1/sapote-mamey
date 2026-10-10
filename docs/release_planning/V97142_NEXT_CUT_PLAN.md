# v9.7.142 Next Cut Plan — SOP-Driven Bug Hunt Route

## Archived cut plan — source and coverage boundary

This plan’s active-base/sign-off claims and apply order concern historical v9.7.142 planning. Preserve
them as history; they do not select the current base or authorize a release. Use [current release-record
owners](../RELEASE_RECORDS_GUIDE.md) and [CUT_PROTOCOL.md](../../CUT_PROTOCOL.md) for current governed
source/test/tier requirements. tools/release_cut.sh mutates release identity/generated sources and runs
its own source-integrity/full-suite/receipt gates; it does not execute this archived apply-order list.
Nothing in this plan authorizes running that script or bypassing the actual owner approval.

The current surrogate owner is tools/run_chatgpt_surrogate_gate.py. It runs a selected subset of existing
tests, optional doctor and syntax checks, not the complete suite. Missing individual declared test files
are filtered out; missing-module failures can become ENV-SKIP, and overall PASS can coexist with skipped
verification. TIMEOUT/FAIL block its summary, but ENV-SKIP does not. Inspect exact discovered file list,
step return codes, skipped/unverified checks and logs; do not use overall PASS as full-suite coverage.
Its output root is created and fixed logs/summary files can be overwritten. py_compile can also create
local cache files. --skip-doctor removes a step; it is not proof doctor passed. Preserve actual receipts
in the single owned candidate and choose destinations explicitly.

The current release_cut full-suite route includes --run-slow and --run-network; its --skip-tests route
requires an exact-source structured external-validation receipt and pinned receipt hash. A surrogate
PASS or explained CHECK is not that receipt. No suite, doctor, build, cut, package copy or source mutation
is requested by opening this document. See [the scoped historical entry](START_HERE_FOR_OTHER_CHATS.md)
for current SOP links and original planning context.

## Retained cut plan

## Status

Do not cut yet. v9.7.141e remains the signed active base.

## Target identity for v9.7.142

v9.7.142 should be a usability + evidence-handling cut, not a broad scoring overhaul.

Primary themes:

1. iterative BLASTP batching,
2. BLASTP follow-up parsing and reprioritization,
3. single-region accession intake handling,
4. C5/C7 deliverable safety,
5. SOP library for ChatGPT/Claude operation.

## Apply order

1. Start from fresh v9.7.141e CODE tier.
2. Apply BGC BLASTP/intake patch stream after Claude feedback.
3. Run BLASTP focused tests.
4. Apply C5/C7 REV2.
5. Apply C5/C7 documentation fixes.
6. Add SOP library.
7. Run focused tests.
8. Run surrogate gate.
9. Build candidate.
10. Hostile-audit candidate before signing.

## Required focused tests

### BLASTP/intake

- `bgc-blastp-panel` first-pass export
- fallback 10–15 protein batching
- giant NRPS/PKS labeling
- `blastp-followup` headerless CSV
- query-title comma recovery
- XML2 optional parse
- more than 10 hits/query preservation
- KY089035 single-region inspect

### C5/C7

- no `SID-XXX` placeholder vignettes
- `build_size_profile.py` root import behavior
- optional DAPR skip visible
- public workbook private-term scan
- macOS dotfile warning doc
- public roster zero doc

### SOP/doc

- SOP files present in release package
- docs index links SOPs
- start-here points ChatGPT/Claude to SOP map
- claim boundary language present

## Candidate sign-off checklist

- [ ] Fresh tree used
- [ ] Apply order recorded
- [ ] Focused tests pass
- [ ] Surrogate gate pass or CHECK explained
- [ ] Real BLASTP examples parse
- [ ] KY089035 inspect behavior passes
- [ ] AS-XXX BLASTP panel smoke passes
- [ ] C5 deliverable build passes
- [ ] C7 public scan passes
- [ ] Manifest/checksums included
- [ ] Release notes include known limitations
- [ ] Hostile audit packet built

## Known limitations allowed in v9.7.142

- Live RID retrieval from NCBI is not required.
- Domain-splitting of giant NRPS/PKS proteins can be a follow-up if giant proteins are clearly flagged.
- AS-XXX BGC005 phosphonopeptide deep proof can remain targeted/optional.
- Full SOP library can include outline-only low-priority SOPs if the master index makes their status clear.
