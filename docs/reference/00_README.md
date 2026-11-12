# Methods reference: start here

These pages explain how the Mamey engine counts, scores and links BGCs, formula by formula.
Read them to write a Methods section or to check where a number comes from.
To run the program, use the [user guide](../GUIDE/00_README.md) and the [tools reference](../user_guides/tools_reference.md) instead.
To read the records in a finished package, use [Read one saved package](../reader/03_READ_RESULTS.md).
Terms are in the [glossary](../GLOSSARY.md).

Read [Check tools: what a PASS does not cover](06_CURRENT_SOURCE_SCOPE.md) before you rely on a volume. It is a selected scope guide: it lists known places where the volumes and check tools differ from the code, not every difference.
If a reference and the code disagree, record the discrepancy and check the owning source.
An implemented formula can still need scientific review.

## Pages in this folder

| Page | Covers |
|---|---|
| [01_Math_Reference_VolI.md](01_Math_Reference_VolI.md) | Edge status, corrected count, assembly tiers, AB/AF/novelty scores, lead tiers, guards, RG-GMCI, coverage |
| [02_Math_Reference_VolII.md](02_Math_Reference_VolII.md) | CCTT triggers, architecture-first calls, KCB/RiQ extraction, compound class, rescue and concordance, Mode B enrichment |
| [03_Plumbing_Reference.md](03_Plumbing_Reference.md) | Retired pointer; the old reference is kept in history |
| [04_RGGMCI_ClusterBlast_Utilization.md](04_RGGMCI_ClusterBlast_Utilization.md) | Why RG-GMCI reads cross-genome ClusterBlast, not only KnownClusterBlast |
| [05_VolII_ClusterG_Figure_System.md](05_VolII_ClusterG_Figure_System.md) | The figure system (Volume II, Cluster G) |
| [06_CURRENT_SOURCE_SCOPE.md](06_CURRENT_SOURCE_SCOPE.md) | Selected limits of the check tools, and known places where the volumes differ from the code |
| [METHODS_TECHNICAL_APPENDIX.md](METHODS_TECHNICAL_APPENDIX.md) | Parameters to report in a Methods section |
| [SCANNER_PFAM_MANIFEST.md](SCANNER_PFAM_MANIFEST.md) | The optional Pfam HMM scanner selectors and how to build the HMM file |
| [STRAIN_MASTER_STORAGE_REFERENCE.md](STRAIN_MASTER_STORAGE_REFERENCE.md) | Detailed storage policy for a Strain Master; start with the [reader page](../DATA_HOME.md) |
| [INTAKE_AND_SMALL_COHORT_POLICY_REFERENCE.md](INTAKE_AND_SMALL_COHORT_POLICY_REFERENCE.md) | Detailed intake, batch and small-sample policy; start with the [reader page](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md) |
| [10_Math_Reference_GeneralAudience.md](10_Math_Reference_GeneralAudience.md) | Retired pointer to Volumes I and II |

Use cited source locations as navigation and check each selected formula against its current owning code, selected version and input scope.

## Authoring aids

- [Layperson guide exemplar](../../examples/layperson_guide_exemplar.md): plain-English guide format.
- [modeb_exemplars/README.md](modeb_exemplars/README.md): example Mode B cards and which profile each one fits.

## Two rules that apply to every number here

- Scores order BGCs for review. They are not evidence that a strain produces a compound.
- KnownClusterBlast and MIBiG matches are similarity, not compound identity.

## Version

When run, `tools/sync_version.py` can update or check the anchored version-of-record lines in Volume I, Volume II, the plumbing pointer and technical appendix. Check the selected release's actual files and command result.
A matching version line does not mean every formula was re-checked at that release.

For what ships in a public release and how the tool behaves offline, see the [public release guide](../PUBLIC_RELEASE_GUIDE.md) and [public release data](../PUBLIC_RELEASE_DATA.md).
