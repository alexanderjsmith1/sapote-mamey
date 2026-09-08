# Engine Reference Documentation

Two tracks, both current as of bundle v9.7.319:

## Technical track (source-cited — every formula → `module.py:symbol`)
- **01_Math_Reference_VolI.md** — core counting, assembly tiers, AB/AF/novelty scoring, lead tiers, floors/guards, RG-GMCI, completeness.
- **02_Math_Reference_VolII.md** — subsystems: CCTT triggers (A), architecture-first (B), KCB/RiQ (C), compound class (D), rescue/concordance (E), enrichment (F).
- **03_Plumbing_Reference.md** — CLI, workbook, figures, packaging, stores, parse layer.
- **04_RGGMCI_ClusterBlast_Utilization.md** — source-verified clarification that RG-GMCI uses cross-genome ClusterBlast, not only KnownClusterBlast.
- **05_VolII_ClusterG_Figure_System.md** — the figure system (Cluster G), completing Vol II.

## General-audience track (prose, no code citations — for readers who want the logic, not the line numbers)
- **10_Math_Reference_GeneralAudience.md** — the full Vol I + Vol II (Clusters A–G) in plain language, including the figure system.

## Authoring guidance
- **layperson_authoring_guidance.md** — plain-English authoring guidance for the `guide` / `compile-report` layperson slots, distilled from the May-27 AS-XXX/AS-XXX prose: the structural arc, a reusable claim-safe analogy library, and the specific moves that made those guides readable — ported without the pre-gate overclaiming (every "makes/produces/kills" rewritten to capacity language).

Both tracks describe the same engine (Mamey v1.9.110 / bundle v9.7.319). The technical track is the
verification reference; the general-audience track is the explainer. Where they touch the same
formula they agree; the technical track is authoritative on exact constants.

## Public release
- **../PUBLIC_RELEASE_GUIDE.md** — the public (GitHub) release user guide: the release ships complete (nothing is stripped; the Pfam HMM and all fixtures are in place), the tool's runtime network behavior (offline by default; only the optional online BLASTp touches the network), and air-gapped operation. Step-by-step setup in ../../INSTALL.md; provenance and optional HMM rebuild in ../PUBLIC_RELEASE_DATA.md.
