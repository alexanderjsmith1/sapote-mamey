# Figure Factory preflight and methods manual

*Current to bundle v9.7.405 · engine Mamey 1.9.145. Authored by Codex (Wiki Revision 03, 2026-08-31) against v9.7.395; admitted to the bundle wiki at v9.7.405 by the Claude Code patch lane after a currency pass. Documentation only — confers no scientific, release, or publication authority; class-level hypotheses, judgment deferred.*

Figure Factory is an additive renderer of admitted evidence. It does not discover evidence, change a score, repair a Mode B gap, accept a scientific interpretation, or authorize release or publication.

## Integrated deliverable

Figure Factory is an integrated, expected deliverable rather than an optional hand-run tool. In the integrated flow it is invoked as the Mamey subcommand `python mamey_run.py figure-factory --config <json>` and auto-emitted after the package seal and cohort assembly, so an aggregate evidence-coverage figure is part of the normal run/cohort deliverable set. The integrated subcommand and its auto-emit wiring are delivered by the companion CLI/cohort wiring lanes; this manual is the preflight and methods contract they render against.

The direct driver `python tools/figure_factory_next.py --config <json>` remains the advanced/manual path. It calls the same `build()` and produces identical artifacts; use it for one-off renders, configuration development, and debugging outside the run/cohort flow. Presenting Figure Factory as a first-class deliverable does not weaken any preflight rule below: every gate, refusal, and claim ceiling applies identically whether the renderer is reached through the subcommand or the manual driver.

### R / ggplot2 + ggtree export companion

The plotted-data sidecar that travels with every figure is what makes each figure restyleable in R without re-running the pipeline. The Figure Factory Next renderer writes it as `figure_factory_next_data.tsv`; across the wider figure set each figure carries a tidy `_data.csv` (through `tools/export_figure_ready.py`, whose `figure_ready/*.csv` are named for ggplot2). R templates render publication artwork from those sidecars: `tools/ggtree_placement.R` for phylogeny placement, and the companion `sapote_ggplot2.R` / `sapote_ggtree.R` template set (one function per figure type plus `theme_sapote()`) delivered by the R-export sibling lanes, so a reviewer can reproduce or restyle any figure in ggplot2/ggtree from the shipped data sidecar alone. A figure whose numbers cannot be recovered from its sidecar is not integration-ready. The output-package and methods contracts below govern these sidecars.

### Legacy Diner Menu retired

The legacy "Diner Menu" (`docs/DELIVERABLE_MENU.md`) is retired: it was an early pre-consolidation figure-generation attempt and is not the authoritative deliverable spec. The authoritative deliverable set is the Mamey CLI subcommand surface, in which Figure Factory now appears as the `figure-factory` integrated deliverable; any still-useful figure item from the old menu is folded into this contract and the R-export companion.

## Current implementation boundary

The baseline provides several figure surfaces. Their source and gate contracts differ, so “Figure Factory” must not be treated as one universal runtime behavior.

| Surface | Current v9.7.395 behavior | Documentation consequence |
|---|---|---|
| Figure Factory Next | Reads one content-addressed aggregate TSV under a configured external root; separates channels; applies explicit exclusions; writes PNG, SVG, plotted data, audit-only exclusions, and a receipt. | Safe as a portable aggregate-coverage example when the exact schema and exclusion policy are used. |
| Package/cohort figure commands | Consume sealed package/cohort tables under command-specific gates. | Use installed `--help`, source sidecars, and the figure-specific manifest as option and output authority. |
| Domain figures | Consume post-seal domain tables and can skip non-blockingly when tables or plotting support are unavailable. | Domain figures do not require an authored Mode B card, but their identity and source tables still require current binding. |
| Governed figure-set registry | Defines source artifacts, gates, missingness, denominators, caption templates, methods templates, and claim ceilings. | A registry row is a design/readiness statement, not proof that its source data or rendering exists. |

Two requested preflight rules are not universal current runtime guarantees:

- Figure Factory Next refuses when no eligible rows remain, but it can currently render rows whose numerators are all zero. The universal `OUTPUT_REFUSED_ALL_ZERO` rule below is a proposed documentation and implementation contract.
- Figure Factory Next supports explicit `distinct_references`, but v9.7.395 does not define a field named `external_benchmark` or a universal default-off benchmark switch. The external-benchmark rule below is a proposed documentation and implementation contract.

An integrator must retain these two implementation holds. Do not rewrite them as already enforced by every v9.7.395 figure path.

## Preflight before any render

Complete preflight in this order:

1. **Name the scientific question.** State the measure, unit, scope, and whether the output is evidence-only, Mode-B-dependent, or mixed.
2. **Bind the input.** Record logical locator, SHA-256, bytes, schema, row count, bundle/engine version, and the exact package/cohort/run receipt.
3. **Validate identity.** Any individual-locus row displays `strain / full node-or-contig / region / BGC alias`. Protein/domain rows add the protein or domain-sequence identity key.
4. **Declare the denominator.** Record included, excluded, missing, gated, and observed-zero rows. Never infer a denominator from plotted marks.
5. **Keep channels separate.** Do not pool nr, ClusteredNR, local Swiss-Prot, MIBiG, ClusterBlast, BiG-SCAPE, RG-GMCI, cohort, domain, literature, activity, or judgment states into one unlabeled score.
6. **Apply privacy and exclusion policy.** Exclusions are resolved before aggregation and receive an audit-only receipt. Excluded identities must not leak into render-facing data.
7. **Resolve boundary and comparison scope.** Preserve boundary/overmerge/rescue states, genus strata, engine/profile compatibility, and any comparator or benchmark role.
8. **Run empty and all-zero tests.** Empty eligible input and all-zero eligible measures are typed refusals, not blank or misleading figures.
9. **Check the output target.** Use an additive destination. Refuse a non-empty collision unless the owning command explicitly defines safe atomic replacement.
10. **Prepare sidecars.** Plotted data, caption, methods, source fingerprints, exclusions, and a render receipt travel with the image.
11. **Validate independently.** Data/figure agreement, layout, legibility, privacy, and claim language are separate checks. A render pass is not scientific or publication approval.

## Typed refusal surface

The manual uses the following preflight vocabulary. “Proposed” means an integrator must not claim universal runtime enforcement until the owning code and tests adopt the state.

| State | Trigger | v9.7.395 binding |
|---|---|---|
| `OUTPUT_REFUSED_INCOMPLETE_IDENTITY` | An individual-locus row lacks one of the four identity fields or conflicts with the source package. | Exact-locus contract is source-confirmed; universal figure wiring requires rebind. |
| `OUTPUT_REFUSED_INPUT_HASH_DRIFT` | Input bytes do not match the declared SHA-256. | Implemented by Figure Factory Next. |
| `OUTPUT_REFUSED_NO_ELIGIBLE_ROWS` | Policy and gates leave no renderable rows. | Implemented by Figure Factory Next. |
| `OUTPUT_REFUSED_ALL_ZERO` | Every eligible plotted numerator/value is zero after policy and gate application. | Proposed universal rule; only some current figure paths suppress/drop all-zero output. |
| `OUTPUT_REFUSED_UNDECLARED_GENUS_POOLING` | A comparison pools known different genera or unknown genus without a declared cross-genus design. | Proposed manual rule grounded in current genus/comparator cautions. |
| `OUTPUT_REFUSED_EXTERNAL_BENCHMARK_UNDECLARED` | An external benchmark/reference enters render or denominator data without explicit opt-in and receipt. | Proposed universal rule; current `distinct_references` is explicit but is not a named benchmark switch. |
| `OUTPUT_REFUSED_INVALID_DENOMINATOR` | Denominator is missing, nonpositive, incompatible, or smaller than numerator. | Implemented by Figure Factory Next for its schema. |
| `OUTPUT_REFUSED_EXCLUSION_DRIFT` | A required exclusion policy matches zero rows or leaks into rendered data. | Implemented by Figure Factory Next. |
| `OUTPUT_REFUSED_EXISTING_NONEMPTY_OUTPUT` | Destination already contains material outputs and the owning command lacks a safe replacement contract. | Command-specific; retain as a preflight check. |
| `OUTPUT_REFUSED_MISSING_CAPTION_METHODS` | Image would be emitted without the required data, caption, methods, source, and receipt sidecars. | Registry/source-bundle design requirement; universal wiring requires rebind. |

### All-zero refusal

Zero is valid only when a named measurement or deterministic test ran against a positive declared denominator. Missing, unbound, not-run, gated, and structurally unavailable are not zero.

After exclusions and gates:

- if no eligible rows remain, emit `OUTPUT_REFUSED_NO_ELIGIBLE_ROWS`;
- if eligible rows remain but all plotted numerators or values are zero, emit `OUTPUT_REFUSED_ALL_ZERO` and a receipt; and
- if at least one eligible value is nonzero, render while retaining every verified zero and every nonzero row required by the declared denominator.

The all-zero receipt should include the input hash, row count, denominator keys, policy/exclusion counts, proof that all eligible values are zero, and the claim ceiling. It should not emit an image. This avoids turning an empty-looking visual into a biological negative or a false assertion that every channel was measured.

## Genus-aware comparisons

Genus is a comparison stratum, not a decorative label.

For every genus-aware figure:

- bind genus from a governed taxonomy field or crosswalk; never infer it from a strain identifier;
- retain `UNKNOWN` as its own state and review it rather than silently assigning or discarding it;
- declare whether the scientific question is within-genus, cross-genus, or genus-faceted;
- compare capacity scores only across compatible engine versions and profiles;
- show per-genus numerator and denominator, including exclusions and missingness;
- label off-target or unresolved organisms separately from the governed actinomycete cohort;
- keep same-genus and cross-genus comparators visibly distinct; and
- state that a genus match strengthens context but does not establish product, function, or pathway identity.

For BiG-SCAPE or other family-derived counts, “private,” “singleton,” and “reference-dark” describe the panel and reference set. They are not organismal rarity or novelty. Genus-matched comparators plus additional low-similarity evidence may support a novelty candidate; panel privateness alone does not.

## External benchmark is default-off

An external benchmark is a control, reference cohort, published comparator, or external study object not already admitted as part of the governed study denominator.

The proposed default is `external_benchmark = OFF`.

Presence on disk, discovery under an external data root, a familiar label, or a `distinct_references` entry does not turn an object into an admitted benchmark. Enabling one requires an explicit benchmark ledger with:

- stable benchmark ID and role;
- logical locator, SHA-256, bytes, and source/license/provenance;
- engine, antiSMASH, database, and schema compatibility as applicable;
- genus/taxonomy relationship to the study set;
- exact inclusion rationale and claim ceiling;
- a separate benchmark denominator;
- sensitivity output with and without the benchmark; and
- caption language that labels it as an external benchmark rather than a study member.

The benchmark remains visually and numerically distinct from the study cohort. It must not change a study denominator, score, ranking, novelty label, or biological conclusion silently. If the benchmark is absent or disabled, report `EXTERNAL_BENCHMARK_OFF`; do not report biological absence.

`distinct_references` in Figure Factory Next is a narrower explicit-retention mechanism. It prevents a reference row from being conflated with an excluded identity. It does not by itself satisfy the full external-benchmark contract above.

## Boundary, overmerge, and contig rescue in figures

Figures must preserve the same three-way distinction as Mode B.

| State | Figure treatment | Caption requirement |
|---|---|---|
| Boundary/truncation | Stratify or encode Interior, Edge, Full-contig, and unknown without converting them into one completeness score. | State boundary denominator and that apparent counts/lengths may reflect fragmentation. |
| Within-locus overmerge | Show protocluster/system decomposition when available; mark region-level aggregates as potentially composite. | State whether length, KCB, gene, or domain values are region-level or decomposed. |
| Cross-contig rescue | Draw candidate relationships only from admitted pair evidence; keep both full identities and component evidence. | Use “candidate linkage, not nucleotide join”; do not draw a continuous physical pathway without sequence proof. |

A dashed candidate edge can express an explicitly declared hypothesis. It cannot imply nucleotide adjacency. A region-level comparator score in an overmerged locus cannot be transferred to every protocluster.

## Figure dependency classes

Dependency is determined by the plotted source, not by where a figure is discussed. A figure mentioned in Mode B §18 is not automatically Mode-B-dependent.

### Evidence-only: no authored Mode B required

These classes may be built from sealed deterministic or post-seal evidence when their own source gates pass:

- inventory, class, boundary, length, and corrected-count summaries;
- deterministic AB/AF and novelty routing-prior views, labeled as priors;
- gene roster, locus map, domain burden, domain strip, module, substrate, and active-site views;
- CCTT, transport, resistance, regulation, and TTA source-derived capacity views;
- KCB/MIBiG, ClusterBlast, BiG-SCAPE, and RG-GMCI supporting views under explicit source/run identities;
- cohort prevalence and evidence-availability views with governed denominators; and
- Figure Factory Next aggregate evidence-coverage figures.

These figures cannot claim a final Mode B judgement, product identity, measured activity, owner-selected biological model, or publication readiness.

### Mode-B-dependent

These classes require a saved, validated current-profile card or an explicitly accepted judgment ledger as their plotted source:

- final Mode B judgement or disposition summaries;
- supported-model versus alternative-model figures;
- experimental decision-tree or owner-selected next-action figures;
- claim-by-claim evidence-provenance disposition figures;
- figures of author-assigned pathway roles not present in deterministic source tables;
- accepted cross-cluster or cross-cohort synthesis derived from card sections; and
- any lead/context emphasis whose declared source is a Mode B judgment or owner ledger rather than deterministic triage.

The receipt must identify the card/profile, saved-byte hash, structure/evidence gate state, owner ledger, and exact plotted fields. A structure pass alone is not acceptance.

### Mixed or conditional

Some topics have both deterministic and Mode-B-derived forms. Lead-context figures are the common example: deterministic triage-prior context is evidence-only, while a figure highlighting an owner-accepted Mode B lead is judgment-dependent. Name the source explicitly and never merge the two states into one “confirmed” category.

## Output package

Every completed figure should travel with:

1. PNG or other requested raster output when supported;
2. SVG or another requested vector output when supported;
3. exact plotted-data CSV/TSV;
4. caption and methods Markdown;
5. source fingerprint sidecar;
6. audit-only exclusion/hold table;
7. render and validation receipt; and
8. a reproducible recipe or command surface.

The plotted-data sidecar is the exact data behind the marks. A replot path may respect governed edits, but edited data becomes a new source object with a new hash and receipt. A PNG without recoverable data and recipe is not an integration-ready figure.

## Detailed caption contract

The caption must let a reader understand what was measured and what was not. Include:

- stable figure ID and title;
- scientific question and publication role;
- bundle/engine and figure-contract version;
- population, scope, exact inclusion/exclusion policy, and denominator;
- measure, unit, aggregation, normalization, and any sensitivity view;
- evidence channel or judgment source, kept separate;
- boundary, overmerge, and contig-rescue treatment;
- genus design and `UNKNOWN` handling;
- external-benchmark state and benchmark denominator when enabled;
- meaning of zero, missing, unbound, gated, and unavailable states;
- identities of highlighted individual loci in complete four-part form;
- source/receipt locator or manifest reference;
- one plain-language reading guide; and
- the exact claim ceiling.

Avoid captions that merely name software, say “reference,” or describe a color without the denominator and evidence source. Use “type strain,” “MIBiG reference,” “external benchmark,” or another precise role.

## Detailed methods contract

The methods sidecar records the reproducible transformation:

- source artifact logical locators, SHA-256 values, bytes, schemas, row counts, and version stamps;
- identity and join keys, including protein/domain sequence hashes where applicable;
- command or entry point, tool versions, material parameters, cutoffs, and random/deterministic settings;
- filters, standing exclusions, privacy exclusions, collision policy, and reason states;
- denominator construction before and after exclusions;
- missingness, observed-zero, and all-zero preflight outcomes;
- genus parsing/crosswalk source and comparison design;
- external-benchmark default/off or explicit opt-in ledger;
- boundary, overmerge, rescue, and run-identity treatment;
- calculation or aggregation formula for every plotted value;
- output file list, hashes, byte counts, and sidecar relationships;
- data/figure, privacy, layout, and claim-safety validation results; and
- citation status and unresolved owner holds.

Caption and methods text are data products. They receive hashes and remain bound to the exact image and plotted-data sidecar.

## Claim ceiling

A Figure Factory `PASS` is rendering, reconciliation, and policy QA for the recorded inputs. It is not biological validation, Mode B acceptance, owner approval, integration, release approval, or publication approval.
