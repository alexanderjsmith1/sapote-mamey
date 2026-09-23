# Sapote-Mamey Bundle Release Manifest — v9.7.440 CODE archive

**Cut/build date:** 2026-09-22
**Artifact status:** CI correction candidate  
**Bundle version:** `sapote-mamey-v9.7.440`  
**Authoritative bundle version:** `9.7.440`  
**Engine:** Mamey v1.9.169  
**Build stamp:** 20260922v97440c  
**Release profile:** `CODE`

This manifest identifies and summarizes validation of the source tree embedded in the CODE tier.
This CODE archive carries a checksum and test receipts. Software validation does not establish an accepted biological analysis.

## Tier scope

This single CODE archive contains portable program source, user documentation, tests, generic
fixtures and release tooling. External databases and project analysis data remain separate.
No additional release tiers are included in this CODE archive.

## Current validation

| Gate | Status |
|---|---|
| Full pytest suite | PENDING GitHub CI rerun after receipt-hash spacing correction; previous v9.7.440 local validation does not validate this correction |
| Focused verification | 1145 passed / 14 skipped on the corrected b source; c identity and extracted checks recorded in the accompanying receipt |
| Strict repository health | PASS (1306 observed direct print calls; enforced ceiling 1280 under the recorded narrowing owner waiver) |
| Version synchronization | PASS |
| Generated module, tool, command, and deliverable inventories | PASS |
| R source parsing | PASS (17 bundled R sources parsed with Rscript); live rendering and external-tool pilots remain separate |
| Release tier builds and archive checksums | One CODE archive; no additional tiers included |
| Archive integrity | PASS (ZIP CRC, extracted checksums and identity) |

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

Naming rule for any future multi-tier release: All four tiers share build stamp `20260922v97440c`. No such tier set was built here.

| Gate | Status |
|---|---|
| `sync_version --check` | PASS (engine 1.9.169, bundle 9.7.440) |

All tracked version anchors at v9.7.440 / Mamey 1.9.169.
`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v9.7.440.
