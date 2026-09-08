# Sapote–Mamey v9.7.22 — release notes (builds -i … -p)

Engine `mamey 1.9.30`. Four tiers: CODE, CODE-analysis-free, SID-public (public; AS-### free) and
MERGED-PRIVATE-scaffold (retains AS refs by design). All builds verified in-zip (pytest + checksum
self-verify + anchor-free leak scan).

## -i … -j — hard-guard leak fix
Real strain IDs are underscore-wrapped (`_AS-NNN_`); every scrub/audit used a `\b` word-boundary that
skips `_`, so the bundle had been mis-certifying public tiers. Fix: anchor-free hyphenated pattern
`(?<![A-Za-z])AS-[0-9]{2,4}` (preserves the public `AL-KSAMP_AS10_SC01` substring), real refs scrubbed
in all 3 public tiers, and a **fail-closed invariant** (`test_no_unpublished_ids_in_public_tier.py`)
that skips on the private tier. Piericidin added (75th reference).

## -k — audit hardening
AST/tokenize-aware public redactor (scrubs comments+strings only, never code identifiers); per-tier
`TIER_MANIFEST.txt` + invariant pytest before zip; Mode B completeness guard (no mismatched all-`?`
cards on incomplete input); single-strain + CI-fixtures docs.

## -l — antiSMASH-profile comparability
`--antismash-profile` threaded into manifest/receipt + a cross-profile pooling guard. Cheap-debt:
`esmeraldin` KNOWN_MISFIRE, `BUILD_STAMP.txt` as version SSOT, canonical glossary.

## -m — RG-GMCI / reconstruction acceptance gates
Overlap-fraction geometry gate: convergence-count-only HIGH demoted to LOW_SHARED_REFERENCE_SIGNAL
without good geometry or a cross-scaffold split; reconstruction verdict gated on shared-reference
overlap fraction. 14-test matrix.

## -n — fragment-concordance scorer
`fragment_concordance_scorer.py`: scores observed fragments vs reference architecture signatures over
region / marker-set / domain-shape / size. Claim-safe (marker credit only from adjudicated
expected_marker_set; T43 [E-signal]).

## -o — UX layer
`START_HERE.md` task router; `id_resolver` module + `build_id_resolver.py` emitting
`BGC_ID | bgc_uid | contig/NODE | region | antiSMASH file | workbook row`, wired into Mode B reports.

## -p — MIBiG 4.0 integration
A broad, current reference base with the curation as a thin overlay:
- `mamey/data/mibig/mibig_reference_index.bacterial.json` — 2,091 confirmed-bacterial BGCs (21 phyla,
  0 retired), auto-extracted from MIBiG 4.0 JSON+GBK; KS/A/C from `aSDomain`, size from `LOCUS`,
  `provenance="MIBiG-4.0-auto"`, markers `[]` (no curated T43).
- `mamey/data/mibig/adjudications.json` — accession-keyed curated overlay (75 entries: marker sets,
  verdicts, capacity flags) lifted from `reference_bgc_library.json`. Carries no BGC selection.
- `mamey/adjudication.py` merges them: matched accession → CURATED-ADJUDICATED (marker credit, KS
  disagreement flagged); else MIBIG-AUTO (region+size-dominant, no marker credit).
- `fragment_concordance_scorer.py --mibig-index` scores against the adjudicated 2,091-entry space;
  output carries `reference_tier` + `best_accession` per match.
- The public MIBiG corpus is exempt from the AS-### leak scan (third-party public data; contains the
  public enterocin bacteriocin BGC0000489). Validation: 65/70 curated KS match auto; 5 flagged.
