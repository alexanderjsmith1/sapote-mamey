# Sapote-Mamey Bundle Release Manifest — v9.7.428 quality-recheck candidate

**Cut/build date:** 2026-09-11  
**Candidate status:** controlled quality-recheck rebuild; not signed release  
**Bundle version:** `sapote-mamey-v9.7.428`  
**Authoritative bundle version:** `9.7.428`  
**Engine:** Mamey v1.9.163  
**Build stamp:** 20260911v97428a  
**Release profile:** `CODE`

This manifest identifies and summarizes validation of the source tree embedded in the CODE tier.
The outer release directory records the archive-level seal: `_cutlog.txt` files describe each tier
and `SHA256SUMS.txt` binds the completed ZIPs. This source manifest cannot contain the hash of the
archive that contains it.

## Tier scope

The CODE tier contains the portable program, user documentation, tests, generic fixtures, and
release tooling. External databases and private analysis data are separate. The required release
set also contains the analysis-free CODE tier, the public cohort tier, and the public-release tier;
an optional merged private scaffold may be cut alongside them.

## Current validation

| Gate | Status |
|---|---|
| Full pytest suite | PASS (10942 passed, 237 skipped; operator-supplied counts, no log bound) |
| Candidate-focused tests | PASS (bioassay, phylogeny, portability, navigation, and release surfaces) |
| Strict repository health | PASS (1322 observed direct print calls; enforced ceiling 1280 under the recorded narrowing owner waiver) |
| Version synchronization | PASS |
| Generated module, tool, command, and deliverable inventories | PASS |
| R source parsing | PASS (12 scripts); real-data rendering remains an integration check |
| Release tier builds and archive checksums | Recorded externally by `tools/release_cut.sh` in the release directory |
| Local release seal | Determined by the external cut log and archive checksum receipt |

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

All four tiers share build stamp `20260911v97428a`.

| Gate | Status |
|---|---|
| `sync_version --check` | PASS (engine 1.9.163, bundle 9.7.428) |

All tracked version anchors at v9.7.428 / Mamey 1.9.163.
`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v9.7.428.

*Generated: 2026-09-11 | Sapote-Mamey Bundle v9.7.428 | NOT_FOR_PUBLIC_RELEASE*
