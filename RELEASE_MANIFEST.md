# Sapote-Mamey Bundle Release Manifest — v9.7.431 internal review candidate

**Cut/build date:** 2026-09-14  
**Candidate status:** controlled quality-recheck rebuild; not signed release; internal review base only  
**Bundle version:** `sapote-mamey-v9.7.431`  
**Authoritative bundle version:** `9.7.431`  
**Engine:** Mamey v1.9.165  
**Build stamp:** 20260914v97431a  
**Release profile:** `CODE`

This manifest identifies and summarizes validation of the source tree embedded in the CODE tier.
This is an internal CODE review archive with an external checksum and test receipts. It is not a public release or an accepted biological analysis.

## Tier scope

This single CODE archive contains portable program source, user documentation, tests, generic
fixtures and release tooling. External databases and project analysis data remain separate.
No additional release tiers are produced for this internal review cut.

## Current validation

| Gate | Status |
|---|---|
| Full pytest suite | PASS (11179 passed, 298 skipped; receipt-bound log) |
| Candidate-focused tests | 68 passed / 13 skipped; generated/version checks 38 passed; final status and integrity checks recorded externally |
| Strict repository health | PASS (1322 observed direct print calls; enforced ceiling 1280 under the recorded narrowing owner waiver) |
| Version synchronization | PASS |
| Generated module, tool, command, and deliverable inventories | PASS |
| R source parsing | NOT RUN here: Rscript unavailable; other-laptop validation requested |
| Release tier builds and archive checksums | One internal CODE archive only; no multi-tier release performed |
| Local release seal | NOT SEALED for public release |

Skipped tests are gated tests whose required local data or external tools are not shipped. A skip
does not demonstrate that the associated live workflow ran. Test success establishes software and
fixture behavior; it does not establish scientific interpretation or owner acceptance.

## Material limits at this cut

- The bioassay Figure Factory supplies a typed planning and rendering contract. It has not ingested
  the project's heterogeneous raw 96-well, 384-well, or in-vivo datasets in this cut.
- GToTree and EPA-ng paths have deterministic adapters and tests. A new-machine run with external
  tools, downloaded references, and real strain data remains required integration evidence.
- Phylogenetic placement is context, not a species assignment. Genus conflicts and contaminated or
  incomplete 16S queries remain explicit review states.
- Mode B consumes admitted, provenance-bound evidence. Similarity, capacity, phylogenetic proximity,
  bioassay context, or a database listing does not establish compound production.
- Publication and any public GitHub release remain owner actions.

## Derived sync anchors

Naming rule for a future multi-tier release: All four tiers share build stamp `20260914v97431a`. No such tier set was built here.

| Gate | Status |
|---|---|
| `sync_version --check` | PASS (engine 1.9.165, bundle 9.7.431) |

All tracked version anchors at v9.7.431 / Mamey 1.9.165.
`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v9.7.431.

*Generated: 2026-09-14 | Sapote-Mamey Bundle v9.7.431 | NOT_FOR_PUBLIC_RELEASE*
