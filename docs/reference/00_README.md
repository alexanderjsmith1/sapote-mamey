# Methods reference: start here

These pages explain how the Mamey engine counts, scores and links BGCs, formula by formula.
Read them to write a Methods section or to check where a number comes from.
To run the program, use the [user guide](../GUIDE/00_README.md) and the [tools reference](../user_guides/tools_reference.md) instead.
The [metadata reader guide](../BUNDLE_METADATA_READERS.md) explains the package records.

Read [current source scope](06_CURRENT_SOURCE_SCOPE.md) first. It lists where the older volumes no longer match the code.
If a reference and the code disagree, record the discrepancy and check the owning source.
An implemented formula can still need scientific review.

## Technical track (cites the source module for each formula)

| Page | Covers |
|---|---|
| [01_Math_Reference_VolI.md](01_Math_Reference_VolI.md) | Edge status, corrected count, assembly tiers, AB/AF/novelty scores, lead tiers, guards, RG-GMCI, coverage |
| [02_Math_Reference_VolII.md](02_Math_Reference_VolII.md) | CCTT triggers, architecture-first calls, KCB/RiQ extraction, compound class, rescue and concordance, Mode B enrichment |
| [05_VolII_ClusterG_Figure_System.md](05_VolII_ClusterG_Figure_System.md) | The figure system (Volume II, Cluster G) |
| [03_Plumbing_Reference.md](03_Plumbing_Reference.md) | CLI, workbook, figures, packaging, stores, parse layer |
| [04_RGGMCI_ClusterBlast_Utilization.md](04_RGGMCI_ClusterBlast_Utilization.md) | Why RG-GMCI reads cross-genome ClusterBlast, not only KnownClusterBlast |
| [METHODS_TECHNICAL_APPENDIX.md](METHODS_TECHNICAL_APPENDIX.md) | Parameters to report in a Methods section |
| [SCANNER_PFAM_MANIFEST.md](SCANNER_PFAM_MANIFEST.md) | The optional Pfam HMM scanner selectors and how to build the HMM file |

## Plain-language track

- [10_Math_Reference_GeneralAudience.md](10_Math_Reference_GeneralAudience.md) covers Volumes I and II without code citations.
  Use the technical track to locate exact constants, then check the owning source before quoting them.

## Authoring aids

- [Layperson guide exemplar](../../examples/layperson_guide_exemplar.md): plain-English guide format. The older style notes are retired to [history](../history/retired_458/reference/layperson_authoring_guidance.md).
- [modeb_exemplars/README.md](modeb_exemplars/README.md): example Mode B cards and which profile each one fits.

## Two rules that apply to every number here

- Scores order BGCs for review. They are not evidence that a strain produces a compound.
- KnownClusterBlast and MIBiG matches are similarity, not compound identity.

## Version

`tools/sync_version.py` updates the "Version of record" line in Volume I, Volume II and the plumbing reference at each cut.
A matching version line does not mean every formula was re-checked at that cut.
The general-audience page carries its own dated note, which does not update.

For what ships in a public release and how the tool behaves offline, see the [public release guide](../PUBLIC_RELEASE_GUIDE.md) and [public release data](../PUBLIC_RELEASE_DATA.md).
