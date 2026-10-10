# Reporting v2 — per-gene MIBiG convergence & structured antiSMASH tables

*Engine 1.9.114 (bundle v9.7.332), Codex **P_MPG + P_LWC**. This is the operator/authoring
reference for the outputs that cut adds. **Read this before citing any of the new fields or
tier labels in a Mode-B card, a manuscript, or a slide.***

## What this is — and is not

These are **new deterministic reporting outputs**, not new judgments and not a scoring change.
Multi-gene convergence is **direct sequence evidence for pathway-family relatedness**. It does
**not** prove exact product identity, expression, production, bioactivity, resistance, novelty, or
physical linkage across contigs. The tiers below are **reporting strata, not Sapote judgments** —
they stratify how much per-gene reference agreement a BGC shows, nothing more.

**Source-scoped reporting boundary:** the current extraction `scoring.py` and `rules.py` do not directly consume this module. Current downstream consumers also include comparator-coverage, gene-first exploration, roster, widget and other report paths, so the old “only three importers” statement is not a current consumer inventory. There is no AB/AF bonus from convergence — the
"report-only" contract holds in the import graph. The modules carry it in code:
`mibig_per_gene.REPORT_ONLY_CONTRACT = "REPORT_ONLY_NO_SCORING"`,
`length_weighted.TRIAL_ONLY_NO_SCORING`, and a `CLAIM_SAFETY` denial string in `antismash_tables.py`.

## The new package files (sealed gold package, `3_*` prefix)

| file | what it holds |
|---|---|
| `3_mibig_per_gene.{json,csv}` | one retained row per **`(query gene, MIBiG accession)`** pair — the repeated-reference signal (not one best ref per gene) |
| `3_mibig_convergence.{json,csv}` | per **BGC × MIBiG accession**: distinct query/subject genes, query-gene share, recognizable-gene share, median/min identity, median coverage, best antiSMASH reference rank, class concordance, boundary status, **evidence tier** |
| `3_mibig_profile.csv` | per BGC: dominant accession, compound-family label, gene count, tier (denominator = all query-cluster genes, so the dark-matter fraction stays meaningful) |
| `3_antismash_structured.json` | combined structured module/RiPP/motif/RRE-Finder evidence |
| `3_antismash_modules.csv` · `3_antismash_ripp_motifs.csv` · `3_antismash_motifs.csv` · `3_antismash_rrefinder.csv` | the structured tables, split |
| `3_length_weighted_capacity.csv` · `3_length_weighted_summary.json` | P-LWC assembly-sensitivity capacity descriptor (trial; **not a lead score, not a BGC count**) |

Workbook sheets mirror these: `MIBiG_Per_Gene`, `MIBiG_Convergence`, `MIBiG_Profile`,
`antiSMASH_Modules`, `antiSMASH_RiPP_Motifs`, `antiSMASH_Motifs`, `antiSMASH_RREfinder`.

## The evidence-tier vocabulary (deterministic strata)

Computed per BGC from its dominant convergence row. **Thresholds are test-locked at these exact values.**

| tier | requires |
|---|---|
| **H1_HIGH_DENSITY** | ≥12 query genes · median identity ≥70% · median coverage ≥80% · recognizable-gene share ≥0.65 · best reference rank ≤3 · no broad class conflict |
| **H2_STRONG_FAMILY** | ≥8 genes · median id ≥55% · median cov ≥75% · recognizable-gene share ≥0.40 · no class conflict |
| **H3_MULTI_GENE** | ≥4 genes · median id ≥40% · median cov ≥60% · no class conflict |
| **H4_REPEATED_SUPPORT** | ≥2 genes · median id ≥35% · no class conflict |
| **CAUTION_CLASS_MISMATCH** | numerical convergence is real but the **broad antiSMASH/MIBiG classes conflict** — **cannot be promoted**, has hard precedence over every positive tier above |
| **H5_SINGLE_OR_WEAK** | everything else |

`CAUTION_CLASS_MISMATCH` **wins over density**: a 20-gene convergence with a discordant class is
`CAUTION`, not H1. The whole-region query-gene share is reported independently and is **not**
substituted for recognizable-gene dominance.

## How to cite these (authoring guidance)

- **Do** say: *"N proteins converge on the <family> comparator (median id X%, coverage Y%), tier
  H2_STRONG_FAMILY — a related biosynthetic cassette."* Cite strain / full node-or-contig / region / BGC alias, source accession/version and the tier.
- **Do** carry the boundary status: an **edge/truncated** region means the observed annotations are incomplete context; completeness/actionability require separate review even when sequence support is strong.
- **Don't** read a tier as a product call, an activity claim, or novelty. `H2_STRONG_FAMILY` is not
  "this strain makes compound X." The named MIBiG metabolite is a **comparator, not an identified
  product**.
- **Don't** double-count: convergence and KnownClusterBlast derive from the **same antiSMASH
  channel** — they are not independent replication.
- **Coverage >100%** is preserved as-sourced but flagged `SOURCE_GT100_CAPPED_FOR_INTERPRETATION`;
  interpret with the cap, and never silently mutate the source value.

## Backward compatibility

The `reporting_v2_gate` fires **only** when the manifest declares
`reporting_features.schema_version == sapote_reporting_features_v2`. Packages sealed before v9.7.332
return **`LEGACY_NOT_APPLICABLE`** and are not retroactively invalidated. Re-run a strain only to
**obtain** the new tables — existing scoring/counting/triage are unchanged, so cross-strain
comparability is preserved with no re-scoring.

## Provenance / status

The lineage doc cites a trial of 38 AS antiSMASH ZIPs → 1,507 BGCs / 45,767 retained rows / 0 parse
errors. That is a **self-reported trial**; the tier logic is otherwise exercised by unit tests and by
an evidence-free smoke ZIP (which yields 0 convergence rows by design). **A real KCB-bearing strain
run is still owed before the convergence tiers are trusted on live output.** Until then, treat
live-run tiers as provisional.

## Current denominator, aggregation and missingness contracts

`mamey/mibig_per_gene.py:101–178` maps knownclusterblast TXT files to contig+region, then stores rows under BGC alias. Duplicate context keys can overwrite; unmapped files are skipped. Versioned references are collapsed at the first dot for the query/reference key, and the highest BLAST-score subject row is retained for each query/reference pair. This is not reciprocal one-to-one gene matching. Keep source file, full reference version and full locus map separately. Per-file exceptions increment `parse_error_count`; overall status can still be `PASS` when other rows exist. `NULL_NO_MIBIG_GENE_HITS` conflates empty/unavailable/skipped/failed parsing unless source/error context is inspected. CLI catches module-level exceptions into `ERROR_<type>` with empty per-gene data (`mamey/cli.py:1831–1861`).

The query denominator comes from the parsed query table **plus hit-derived fallback genes**, not a verified complete CDS roster. Trimmed/missing query tables can shrink the denominator and inflate fractions. In convergence, “recognizable” means hit-bearing query genes; in the BGC profile it applies the profile's minimum-identity rule. These two recognizable denominators are not interchangeable (`mibig_per_gene.py:126–140,181–244,267–303`). `KNOWN_ANCHORED` is an accession-pattern anchor plus profile fraction≥0.20, not compound identity or accepted reference biology. The dark-matter names are saved-annotation reporting labels, not novelty findings.

Raw coverage and capped interpretive coverage remain separate. Missing/non-numeric coverage is flagged, but helpers are not comprehensive finite-number admission guards; independently reject invalid values before interpreting tiers. Tier code uses capped interpretive median; raw median is for provenance (`:24–46,292–313,438–458`). A class-discordant reference receives CAUTION, but dominant sorting places that reference after positive tiers from **other references**: mismatch precedence is per reference, not a universal BGC veto. Dominant status and runner-up margin must travel with the tier; tier-first ordering can make a lower-density positive reference dominant over a larger mismatch (`:350–399`).

The reporting gate checks declared schema, files, row/header/count and workbook parity. It is not an exact source-byte/full-locus/biological validator. `LEGACY_NOT_APPLICABLE` applies to undeclared reporting schema, not a retroactive claim that legacy evidence is complete (`mamey/validate.py:83–118,737–750`). Package sealing/hash validation and current50 authoring verification are separate boundaries. Re-running an old package is a separately authorized new run, not an in-place upgrade or guarantee that all current extraction/scoring behavior equals .332.

The old 38-ZIP/1,507-BGC/45,767-row trial remains a self-reported historical scope. No runtime trial, test suite, import-graph proof, scientific adoption or current live-output validation was performed here. Freeze exact source ZIP/package/sidecar/code hashes and parameters before citing a convergence result; report uncertainty and denominator completeness alongside reference agreement. See [current ranker admission](DEFINITIVE_BGC_RANKER.md) for the additional limits of consuming these per-gene tables.
