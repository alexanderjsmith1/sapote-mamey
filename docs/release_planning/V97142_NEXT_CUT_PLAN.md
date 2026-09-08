# v9.7.142 Next Cut Plan — SOP-Driven Bug Hunt Route

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
