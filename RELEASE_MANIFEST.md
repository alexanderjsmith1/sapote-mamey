# Sapote-Mamey Bundle Release Manifest — v9.7.461 CODE archive

**Cut/build date:** 2026-10-29
**Artifact status:** validated CODE archive  
**Bundle version:** `sapote-mamey-v9.7.461`  
**Authoritative bundle version:** `9.7.461`  
**Engine:** Mamey v1.9.177  
**Build stamp:** 20261029v97461a  
**Release profile:** `CODE`

This manifest identifies and summarizes validation of the source tree embedded in the CODE tier.
This CODE archive includes `SOURCE_CHECKSUMS_SHA256.txt`. Test logs and the seal receipt are kept outside the archive. A seal is an external `SEAL_RECEIPT.json` that records the archive hash; this manifest is not a seal. Passing tests do not validate a biological analysis.

## Tier scope

This single CODE archive contains portable program source, user documentation, tests, generic
fixtures and release tooling. External databases and project analysis data remain separate.
No additional release tiers are included in this CODE archive.

## Current validation

| Gate | Status |
|---|---|
| Full pytest suite | PASS (23071 passed, 297 skipped; receipt-bound log) |
| Focused verification | New portable adapter, identity, containment and clinker regressions pass; exact counts recorded in external candidate receipts |
| Strict repository health | PASS (1250 observed direct print calls; enforced ceiling 1255; no waiver. The ceiling's history is in `PRINT_WARN_THRESHOLD`, `tools/repo_health.py`.) |
| Version synchronization | PASS |
| Generated module, tool, command, and deliverable inventories | PASS |
| R source parsing | PASS (all bundled R sources parsed); synthetic single/grouped tree-track PDF pages inspected; live experimental integration remains separate |
| Release tier builds and archive checksums | One CODE archive; no additional tiers included |
| Archive integrity | ZIP CRC, extracted-suite results and local seal decision are bound by the external SEAL_RECEIPT.json beside the sealed archive |

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

Naming rule for any future multi-tier release: All four tiers share build stamp `20261029v97461a`. No such tier set was built here.

| Gate | Status |
|---|---|
| `sync_version --check` | PASS (engine 1.9.177, bundle 9.7.461) |

All tracked version anchors at v9.7.461 / Mamey 1.9.177.
`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v9.7.461.
