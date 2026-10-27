> These floors belong to the older `mode_b_quality_gate` check. Finished cards use their Mode B
> profile (`full48`, or opt-in `current50_v2`); see the [profile matrix](../MODEB_PROFILE_MATRIX.md) and the
> [walkthrough](../MODE_B_USER_WALKTHROUGH.md). A character count does not measure evidence.

# Mode B — depth policy, data sources, and per-class exemplars

*`DOMAIN_LEVEL_MODE_B.md` describes enrichment inputs. The historical `full30` JSON filename
holds the 48-section default contract; do not infer a section count from the filename.*

## The older quality bar

A substantive card explains the available gene/domain evidence and independent
homology channels in source-bound scientific prose, with contradictions and
reasoned limitations. The passive legacy evaluator measures lexical/structural
proxies; it cannot determine whether a mentioned analysis was performed. Its
main thresholds are:

- **Raised char floors, compressed across tiers:** HIGH 12,000 · MID 11,000 · LOW 10,000.
  Tiers are compressed so an important-but-**fragmented** BGC — which lands at a low rank because it sits
  on a short/edge contig, not because it's less interesting — is no longer dropped to a soft floor. A
  genuine boundary fragment still gets the `FRAGMENT_FLOOR` exemption (assembly reality, not a downgrade).
- **Lexical density proxy:** the evaluator counts regex occurrences of locus-tag
  and domain terms, including repeats, with an absolute minimum of 12. The density
  threshold is `int(character_count / 1000 * MIN_DOMAIN_DENSITY)` with the current
  constant 1.0; it is rounded down, not a strict measured one-per-thousand ratio.
  It does not count verified BLASTp alignments, distinct genes or completed analyses.
  Historic single-card calibration is `UNVERIFIED_HISTORY`, not proof the heuristic
  detects only padding or applies equally to every class.

> **Provisional calibration.** These numbers are anchored on one real §30 card + the depth directive. The
> per-class exemplars below are the real calibration set; expect to revisit whether small classes need a
> class-specific floor once they land.

## This makes multiple rounds/batches the norm — by design

Use as many authoring/review rounds as the selected task needs. First inspect
existing bound domain, gene and channel evidence and deepen the interpretation;
do not add filler or repeat tokens to clear a lexical floor. If a required channel
is unavailable, retain the reason and inference limit. Additional retrieval,
re-parsing, network submissions or package mutations require their own selected
scope and authorization. Batch only the user-selected exact-locus roster; a
quality finding does not authorize an all-BGC or external-service run.

## Where to find the domain-level data (don't infer it — read it)

| Evidence | Source | How |
|---|---|---|
| **aSDomains** | Source ZIP or sealed gene context | For an authorized enrichment task, use the local `python mamey_run.py domain-level --package … --source-antismash …` route. It selects top leads (`--top-n`, default 10), not an arbitrary complete region roster. Source parsing can fall back to limited gene-context names; inspect receipt mode/warnings and reconcile the selected loci before authoring. |
| **Per-gene BLASTp** (identity, positive substitutions, coverage and source identifiers) | Admitted channel outputs and their original query/result receipts | Reuse existing bound results first. `blastp-round` defaults to a local plan: full proteins for top-ranked BGCs (`--full-top`, default 3), representatives for others. A plan is not a search; submission and ingestion are separate authorized actions. Missing results remain unavailable evidence. Percent identity and substitution similarity are distinct measurements. |
| **Domain roles / burden / claim ceiling** | `domain-level` module output | role category + per-BGC burden + safe/unsafe claim pair (architecture/family-level only). |
| **Gene table** (`sec_met_domains`, products) | `<strain>_gene_by_gene_all_bgcs.csv` | note the `sec_met_domains` re-tokenization caveat (micKC↔Pkinase etc.) — weakly-supported, never "lacks domain". |
| **KCB / MIBiG** (similarity, not identity) | `knownclusterblast` / triage `KCB_top` | corpus provenance; feeds §8 and the §24 novelty axis. |
| **Deep domain hits / active sites** | `deep_data.json` (`domain_hits`, `bgc_profile`, `active_sites`) | Check the parsed evidence and per-BGC profile roster. Empty arrays do not establish measured absence; the exporter reads saved evidence rather than a `json_mode` argument. |

Before using these exports in a card, match the profile to the bound `strain / full node-or-contig / region / BGC alias`. Profile rows carry only `sid` and `bgc_id`; domain-hit `region_key` holds the contig value, and hit rows omit the BGC alias and region. Do not treat that field as a complete regional identity or the hit-row count as a unique-domain total. Missing score fields remain JSON `null`.

The deep-dive scaffold accepts absent deep/gene files, substitutes an empty profile when a target has none, and records a target with no verdict as `NO_VERDICT`, with no class call. Its “No modular PKS/NRPS core resolved” text can reflect unavailable profile data. Check the required inputs before adopting that wording; it is not independent verification.

Cite every individual locus as **strain / full node-or-contig / region / BGC alias**
from one bound source record, tag provenance (**store-backed** vs **reconstructed** vs **corpus**), and
keep claim language capacity-level ("consistent with", never "produces"); BLASTp/KCB is similarity, not
identity; bioactivity is extract-level only.

## Format references and historical class sketches

Read [the exemplar reader guide](../reference/modeb_exemplars/README.md) before
reusing a card. The collection contains one full48 typed-terminal format reference
and seven historical class sketches; it does not supply a finished current-profile
card for every listed class. Reuse supported structure and writing register only,
with the selected profile and actual locus evidence. Do not copy omitted sections,
genes, biological conclusions or historical FULL/OK claims into a new card.

## Over-merged regions must address the co-captured class (expect CONTENT_GAP)

The separate `modeb_class_checklist` maps supplied product-label substrings to
concept aliases and returns advisory `CONTENT_GAP` warnings when those words are
absent. The passive `mode_b_quality_gate.evaluate_card` does not perform that
check. Current verification can request the class checklist when product context
is available; missing concepts or a skipped checklist need review.

Explain supported co-captured systems and distinguish them from the intended
protocluster using the actual region evidence. A keyword match does not validate
a biological account, prove over-merging or establish that all class components
are present; retain conflicting and unavailable evidence explicitly.
