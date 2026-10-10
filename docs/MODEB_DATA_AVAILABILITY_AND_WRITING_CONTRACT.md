# Mode B data-availability and writing contract

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


**Status:** normative pre-authoring contract.  
**Command:** `python mamey_run.py modeb-availability`  
**Principle:** inventory evidence before writing prose.

## 1. Purpose

Mode B consumes heterogeneous evidence: the sealed BGC inventory, antiSMASH region records, per-gene context, KnownClusterBlast/MIBiG comparisons, ClusterBlast, per-gene BLASTp, domains/HMMs, selected-gene reviews, GCF context, resistance evidence, literature, cohort context, phenotype observations, prior cards, locus maps, and QA receipts. These streams are not interchangeable and do not share one natural denominator.

The availability module builds a typed inventory before any card is authored. It reports which streams are present, how each stream binds to a locus, which Mode B sections it may support, and which gaps must remain explicit. It does not generate biological prose or upgrade a card.

## 2. Identity hierarchy

The primary key is:

`strain | full assembly node/contig | antiSMASH region`

The display alias `BGC###` is secondary. Evidence states are ordered:

1. `EXACT_LOCUS` — strain, full node/contig, and region match the inventory.
2. `ALIAS_BOUND` — strain and BGC alias match, but the artifact does not independently establish the full locator.
3. `STRAIN_ONLY` — relevant only to the strain or cohort; it must not be localized to a BGC.
4. `UNBOUND` — the artifact cannot be attached to the inventory without a new crosswalk.
5. `ABSENT` — no matching artifact was found in the configured discovery scope.

`ABSENT` and `UNBOUND` are workflow observations, not biological absence.

## 3. Inputs

The required inventory is a header-keyed CSV or TSV with `strain`, `bgc`, `full_node`/`node`, and `region`. Optional fields include `exact_locus`, `folder_path`, and `products`.

Evidence may enter through either or both interfaces:

- `--source-root LABEL=PATH` recursively discovers files under user-configured roots. Roots are runtime configuration. The output observations retain resolved absolute source paths, inventory folder_path is propagated, and the manifest retains absolute output paths. Treat these as local provenance artifacts; the scanner does not sanitize them for distribution.
- `--evidence-index PATH` reads a normalized TSV containing `channel`, `source_path`, identity fields, optional `freshness_state`, and notes.

Tabular discovery is header-aware when enabled, within --table-max-bytes (default 20,000,000 bytes) and the 250,000-row inspection cap. Missing row identity fields may be filled from the path. Oversized/disabled tables, empty groups or caught CSV/read errors fall back to a filename/path discovery candidate. Directory listing errors fail closed, but successful discovery does not establish complete table ingestion; use a curated index and separate source review when completeness matters.

## 4. Outputs

The command writes fixed filenames under `--out`. Existing destinations are accepted and each file is replaced separately; there is no whole-set rollback or destination ownership check. Manifest PASS and exit zero mean the inventory outputs were written, even when individual writing/promotion gates are HOLD. Source files are read in place:

- `modeb_evidence_observations.tsv` — one typed observation per artifact or tabular identity group.
- `modeb_bgc_availability.tsv` — one row per canonical BGC locus, with per-stream state and record counts.
- `modeb_strain_availability.tsv` — per-strain coverage counts without mixing BGC and strain denominators.
- `modeb_section_plan.tsv` — §1–§30 support plan with exact/alias evidence separated from context-only evidence.
- `MODEB_AVAILABILITY_SUMMARY.md` — mechanical audit summary.
- `modeb_availability_manifest.json` — hashes, byte counts, contract id, and counts.

## 5. Writing and promotion gates

`PASS_FOR_GAP_AWARE_AUTHORING` requires:

- an inventory row with normalized node and region fields; and
- a gene-level source (`gene_inventory` or `antismash_region`) bound at exact-locus or alias level.

The draft-eligibility check applies to the supplied inventory. It does not independently compare assembly/sequence hashes, verify source-manifest authority or establish biological correctness/completeness. Those source bindings remain separate required checks.

The normative promotion requirements below exceed the scanner’s implemented indicator. Its promotion_gate checks only blastp_per_gene binding at alias-or-better and an aggregate CURRENT flag. The aggregate selects the strongest binding but treats any observation marked CURRENT as current, even a weaker/unbound row; record counts sum all observations, not only admitted rows. It does not establish every admitted record’s freshness, sequence equality, all-channel readiness, complete roster or finished-profile acceptance. Apply the independent selected-profile checks before promotion.

Promotion remains held while required evidence is `AVAILABLE_UNINGESTED`, `NEAR_READY_ACTIVE_RUN`, `PRACTICALLY_ATTAINABLE`, stale, or freshness-unverified. An absent or `OBSERVED_UNBOUND` row may remain as a reasoned terminal limitation only after readiness is adjudicated as `STRUCTURALLY_UNAVAILABLE` or `NOT_APPLICABLE`, the selected profile's matrix and roster checks pass, and independent content review accepts the claim ceiling. Such a row supplies no bound protein/function evidence. This preserves the ratified separation between document state and evidence state; it does not waive evidence requirements. A filename or modification time does not establish freshness; admitted search evidence must explicitly state `CURRENT` in a normalized evidence index after provenance review.

### Finished-current-evidence BLASTp matrix (default §4; current50 v2 §50)

The default full48 and its legacy `FINISHED_CURRENT_EVIDENCE` alias use §4. A selected `FINISHED_FULL50_CURRENT50_V2` card uses §50; keep the same complete roster and channel separation there. The selected evidence section must contain a subsection titled exactly:

`#### Complete channel-separated BLASTp matrix`

The matrix is a human-review deliverable, not merely a companion-file pointer. It must:

- contain exactly one row for every canonical gene, including boundary/context genes;
- retain the canonical gene order and amino-acid length;
- keep NCBI nr, NCBI ClusteredNR, and local Swiss-Prot separate, with two columns per channel: a named-match column and an alignment-metrics column;
- show the rank-1 accession, complete matched-protein description, and subject organism in every bound-hit named-match cell;
- show rank-1 percent identity, percent positives/similarity, and query coverage in the paired metric cell;
- use the same explicit typed state such as `no bound hit`, `not run`, or `unbound` in both paired cells only after evidence readiness has been adjudicated;
- report per-channel coverage denominators without adding them together; and
- state that ClusteredNR is not nr, percent positives is not percent identity, similarity is not functional proof, and missing evidence is not biological absence.

Before content-QA, every material evidence stream must be classified as one of:

- `READY_BOUND`: integrate now;
- `AVAILABLE_UNINGESTED`: ingest before writing;
- `NEAR_READY_ACTIVE_RUN`: wait, ingest, and keep content-QA blocked;
- `PRACTICALLY_ATTAINABLE`: obtain before content-QA;
- `STRUCTURALLY_UNAVAILABLE`: permit a typed limitation with its reason; or
- `NOT_APPLICABLE`: explain and close.

Only `READY_BOUND`, justified `STRUCTURALLY_UNAVAILABLE`, and justified `NOT_APPLICABLE`
may coexist with content-QA. `Pending` may appear in a work ledger, but it is not an acceptable
terminal cell or prose substitute in a card declaring `FINISHED_CURRENT_EVIDENCE` or
`PUBLICATION_REVIEW_CANDIDATE`. Remeasure exact-gene BLASTP coverage after canonical ingestion;
write `READY_NOW` cards first and preserve other cards as explicitly blocked drafts.

An EBI/UniProt pair is added when that channel is bound, but its absence does not permit the three required channel pairs to be merged or omitted. A percentage plus a bare accession in one cell is not a named match: without the protein description and organism, the human reviewer cannot tell what the percentage describes. A channel-level summary, a selected-core table, or a companion CSV alone does not satisfy the finished-card contract. Draft and gap-aware cards may retain explicit holds, but they must not declare finished-current-evidence or publication-review-candidate status until the matrix and authoritative canonical roster pass validation.

Strain phenotype, ecology, thesis, or literature context may support context sections. None may be back-attributed to a BGC without a separate exact-locus and experimental linkage.

## 6. Section routing

The shipped evidence-stream JSON maps support to the planner’s fixed §1–§30 output. This is legacy planning numbering, not a full48/current50 table of contents or selected-profile verifier. Rebind support to the selected emitted template before writing. A section is emitted in one of three planning states:

- `EVIDENCE_AVAILABLE_REQUIRES_INTERPRETATION`
- `CONTEXT_ONLY_DO_NOT_LOCALIZE`
- `WRITE_EXPLICIT_GAP_OR_HOLD`

The planner never writes the interpretation. Conditional §21–§27 and §29 applicability remains class-dependent and must be resolved by the existing Mode B contract and validators.

## 7. Example

```bash
python mamey_run.py modeb-availability \
  --inventory project/per_bgc_inventory.tsv \
  --source-root package=project/runs \
  --source-root blastp=project/evidence/blastp \
  --evidence-index project/curated_evidence.tsv \
  --out project/modeb_availability
```

Run this command before `emit-modeb-template`, `modeb-round`, or new report prose. The resulting files are a work-order input, not a judgment receipt.

## 8. Claim ceiling

Availability and provenance do not establish biological identity, production, activity, novelty, causality, phenotype, acceptance, release, or publication readiness. Similarity is not identity; capacity is not production; missing or unbound evidence is not biological absence.
