# Cohort rescoring: current provenance checks and historical plan

The preserved engine-1.9.96 plan below records an earlier decision context. It does not authorize rescoring, establish the current cohort roster or validate any biological interpretation. This baseline declares engine **1.9.172**, bundle **9.7.447** (`mamey/__init__.py:1–2`); do not repin a current run to 1.9.96 from this document.

Before comparing existing outputs, inventory the exact strain roster, source paths and SHA-256, package/version receipts, antiSMASH detection profiles, reference assets and scoring configuration. Preserve every individual locus as `strain / full node-or-contig / region / BGC alias`. Equal engine labels alone do not demonstrate equivalent inputs, boundaries or external-evidence coverage. Within-strain ranks can also change across scoring boundaries; the historical assertion that they are unaffected is conditional, not a general invariant.

## What the installed software checks

`tools/cohort_scoring_version_gate.py:42–79,97–111` parses a three-part engine version, rejects empty cohorts and missing/unparseable or unequal version stamps, and exits 1 on those failures. Its CLI scans top-level `*.xlsx` files and reads the first data row of a run-manifest version column (`82–104`); it does not authenticate each BGC's scoring provenance or discover nested workbooks.

The cohort deliverable now calls a version gate (`mamey/cohort_deliverable.py:99–108,112–170,211–236`), so the old proposal to build one is outdated. This integration takes the last manifest row per strain, falling back to the first BGC-master row only if no manifest versions were collected. It compares the observed dominant version, rather than enforcing the installed engine. If the gate module is unavailable or no versions are collected, the integration returns `True` without a certification banner. A mixed-engine synthesis may still be emitted with a warning and a failed uniformity gate. Consequently, file presence or an absent warning cannot certify a complete, current cohort. Also inspect profile provenance; `mamey/cli.py:6184–6190` records strictness and reports explicit/profile disagreement.

## Recovery and claim scope

If provenance differs or is missing, retain the existing evidence with its hold and record the affected identities and version/profile denominators. Reprocessing is a separately governed mutating action with fresh outputs and explicit input/reference/configuration bindings. Do not promise byte-identical rebuilding from a matching version label or carry old rankings into new summaries without comparison. The historical roster, timing estimate, permanent exclusions and claimed surviving mechanisms below require their original evidence and a current source comparison before reuse. In particular, current scoring code treats NAPAA as neutral (`mamey/scoring.py:739–750`), rather than adopting this old exclusion list as current policy.

See [current class vocabulary](DAPR_CLASS_FRAMEWORK.md) and [workflow gates](WORKFLOW_GATES_GUIDE.md).

<details>
<summary>Preserved dated record — historical reference, not an execution request</summary>

# COHORT RE-SCORING PLAN — restoring cross-strain comparability under engine 1.9.96

**Status: PLAN (not yet executed).** This scopes the work; it does not perform it. Nothing in this
document re-scores anything. It exists so the highest-leverage publication blocker is concrete and
ready to run, not a one-line "needs re-scoring" note.

## Why this is blocking (the honest version)

Scoring boundaries stacked across **1.9.84 → 1.9.96** *(observed: the CHANGELOG boundary entries)*.
Each boundary can change a strain's axis scores. Strains in the current cohort were scored at **mixed
engine versions** across that range. Therefore any **cross-strain** comparison (AB/AF capacity ranking,
"top antifungal lead", chemotype prevalence across habitats) is comparing numbers produced by different
rulebooks — **not valid** until every strain is re-scored under one engine. *(inferred from the boundary
model; this is a comparability constraint, not a claim that any individual score is wrong.)*

Within-strain, per-BGC capacity statements are unaffected — they're class-level and engine-version-local.
What's gated is the **comparative layer** specifically.

## Scope: what must be re-run

The 19-strain comparative cohort *(observed: CCSM cohort definition)* — 12 bee / 3 wasp (AS-XXX/365/425)
/ 2 moss (AS-XXX/609) / 2 host-unconfirmed (AS-XXX/348). Re-scoring means, per strain:

1. Re-run the deterministic Mamey extraction on the strain's antiSMASH output under the **pinned 1.9.96
   engine** (no mixed versions). Mamey output is byte-deterministic *(observed: held by tests)*, so this
   is reproducible and checkable.
2. Re-emit the Sapote judgment layer under 1.9.96.
3. Record the engine version **in the per-strain receipt** so provenance is auditable and the next
   boundary can detect staleness automatically.

## The gate that makes this self-enforcing (proposed, not yet built)

Add a **cohort-scoring-version invariant**: a comparative deliverable may only aggregate strains whose
recorded scoring engine == the current engine. Mixed versions → the comparative build refuses (the same
fail-closed pattern as the leak audit and tier-parity gate). This converts "remember to re-score" from a
human checklist item into a gate. *(This would be a new gate row in `gate_registry.tsv`, WIRED to the
comparative-build path — a future cut, not this one.)*

## Cohort-local layers that must be **recomputed**, not concatenated

After re-scoring, the cohort-local layers are recomputed from scratch (they're computed *within* a cohort
and are invalid if carried over): product-class prevalence matrices, pan-genome/BGC family groupings, and
any cross-strain ranking. *(This mirrors the standing merge rule: never concatenate cohort-local layers.)*

## What does NOT change

- The standing permanent exclusions stay excluded from comparative claims: NAPAA (ubiquitous),
  hglE-KS-PREV-001 / hexacosalactone (habitat-non-specific), saccharide class.
- Claim-safety conventions are unchanged: capacity-level language, KCB = similarity, extract-level
  bioactivity, no strain called activity-negative.
- The HSAF/PTM antifungal recurrence across five bee strains *(observed cross-genus within-habitat
  finding)* is a **mechanism** observation, not a score ranking — it survives re-scoring, but its framing
  as the principal comparative finding should be re-confirmed once the cohort is on one engine.

## Estimated shape (not a commitment)

19 strains × (Mamey re-run + Sapote re-emit + receipt stamp). The Mamey step is cheap and deterministic;
the judgment step is the time cost. The output is a re-scored 19-strain cohort + recomputed cohort-local
layers, after which the comparative paragraphs in the methods/NP manuscript can be written against
single-engine numbers. **This is the highest-leverage item on the readiness scorecard.**


</details>
