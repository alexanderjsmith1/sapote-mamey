# Mode B dual-writer / dual-auditor evidence-retention protocol

**Audience:** anyone who writes or audits a Mode B card (the per-locus interpretive write-up). Terms are in the [glossary](GLOSSARY.md).
**Purpose:** let one system or person write a card and a different one audit it, so that polished prose, file names, section counts or self-certification cannot stand in for complete evidence.
**Main rule:** a card with all its sections can still be materially incomplete. The predecessor-to-successor evidence-retention audit is a required gate.

**Commands:** this page defines roles and ledgers, not commands. To author and check a card, use [the Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md) (`emit-modeb-template`, `verify-modeb`). The section list in section 10 is the full48 profile only. For any other profile, take the section list from the [profile matrix](MODEB_PROFILE_MATRIX.md).

## Current implementation and profile boundary

For a new card, choose the [profile](MODEB_PROFILE_MATRIX.md) and follow the
[authoring walkthrough](MODE_B_USER_WALKTHROUGH.md). Use this page for writer and auditor
responsibilities and for predecessor retention. It is guidance, not an automatic role dispatcher or a
runtime state machine. Its numbered section list is the full48 profile. A current50_v2 card has 50
sections and its own template and verifier; keep all 50 and do not cut it to the list below. For
document and evidence states, use the [ratified vocabulary](MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md)
and do not infer approvals from file names.

`mamey/modeb_publication_gate.py` checks specified inline evidence-stream/history dispositions and
section-specific structures; it does not independently enumerate all predecessor artifacts or audit
every retention-ledger value. `mamey/mode_b_receipt.py` has profile-specific, source-bound review checks,
but invoking a basic writer/structure checker does not run that entire review path. Store actual reviewer
identity, selected profile, source hashes, findings and holds. A different system name alone does
not prove independence or owner acceptance. Normative gates remain required when runtime coverage is narrower.

Freeze source evidence by existing path/portable locator and SHA-256; do not duplicate a whole package,
database, report corpus or asset set just to create the source register. Keep one current owned candidate
and authoritative index. The listed deliverable names are a per-card ledger convention, not a requirement
to proliferate copies at every checkpoint. Permission comes from the actual user and task, never a role label or a claimed acceptance. Scientific/release authority remains
with the designated owner under the current task.

## 1. Controlling principles

1. Similarity is not identity.
2. Capacity is not expression, production, activity, or ecological function.
3. Missing, unbound, or un-ingested evidence is not biological absence.
4. Exact assembly + full node/contig + antiSMASH region/interval + sequence/CDS roster controls identity. A BGC alias is display metadata, never a sufficient join key.
5. Every predecessor evidence element must receive an explicit disposition. It may be retained, corrected, superseded, quarantined, declared not applicable, or declared missing. It may not silently disappear.
6. A writer cannot establish publication readiness by completing all full48 sections (§§1–48). An independent audit must first demonstrate evidence retention, exact-source binding, and claim safety.
7. Mamey is deterministic extraction and routing evidence. It informs writing but does not supply product, activity, novelty, merge, or publication judgment.
8. Historical material remains evidence even when its interpretation is superseded. Preserve source bytes and separate useful measurements from stale conclusions.
9. Reference comparisons must identify the reference assembly/record and report identity, coverage, synteny, and source provenance. Host category or compound label alone is not a comparison.
10. The project owner alone accepts a card, authorizes scaling, approves rendering, and determines release/publication status.

## 2. Mandatory display and folder identity

Every deliverable, table, heading, filename, message, ledger, and review note referring to a locus must use:

`strain / full node-or-contig / antiSMASH region / BGC alias`

Example:

`ABC-12 / NODE_7_length_250000_cov_50.000000 / region002 / BGC002`

Never write `BGC002` by itself when referring to a locus. MIBiG accession identifiers such as `BGC0002676.2` are reference-record identifiers and must be labeled as MIBiG accessions.

Recommended folder name:

`<strain>__<full_node_or_contig>__<region>__<BGC_alias>/`

antiSMASH can be run with a looser or more relaxed detection setting than the one the frozen record used. Such runs may renumber aliases. Preserve these only as qualified local aliases, for example:

`ABC-12 / NODE_7_length_250000_cov_50.000000 / region002 / loose-package local alias BGC005`

Never transfer a local alias to the frozen card identity. Crosswalk on the full node, region interval, sequence hash, and CDS roster. Quarantine ambiguity.

## 3. Dual-role operating model

Any system or person may serve as writer or auditor. Assign roles per card, not permanently.

### Writer responsibilities

The writer:

1. freezes and hashes authoritative inputs;
2. establishes exact locus identity and denominator;
3. creates the evidence-retention ledger before prose;
4. extracts every admitted evidence stream;
5. writes the ordered §§1–48 card (full48);
6. includes the complete per-gene evidence table;
7. declares corrections, supersessions, quarantines, and missing evidence;
8. issues a candidate receipt without claiming independent acceptance.

### Auditor responsibilities

The auditor independently:

1. re-resolves the exact locus from sources;
2. checks hashes, source locators, and denominator;
3. compares predecessor, candidate, and source evidence;
4. verifies every retention-ledger disposition;
5. confirms that every section the selected profile requires is present, substantive and correctly ordered: §§1–48 for full48, or the required and applicable conditional sections of `current50_v2`, following that profile's rule for optional sections (see the [current50 guide](MODEB_CURRENT50_V2_CONTRACT.md#required-conditional-and-optional-sections));
6. checks every gene and every BLASTP channel row;
7. challenges product, activity, novelty, ecology, HGT, resistance, prevalence, and cross-contig claims;
8. issues findings without silently rewriting the writer's candidate.

### Independence rule

The same writing pass may run mechanical self-checks, but it may not self-certify `INDEPENDENT_CONTENT_QA_PASSED_CANDIDATE`, `MAINTAINER_ACCEPTED`, or publication readiness. A second system or person, a separate saved task, or a later independent pass must audit it. The auditor reports evidence; the project owner decides acceptance.

## 4. Status vocabulary

Use only this progression:

1. `SOURCE_INVENTORY_ONLY`
2. `DRAFT_NOT_RECONCILED`
3. `EVIDENCE_RECONCILED_CANDIDATE`
4. `INDEPENDENT_CONTENT_QA_PASSED_CANDIDATE`
5. `MAINTAINER_ACCEPTED`
6. `INTEGRATION_APPROVED`
7. `RELEASE_APPROVED`
8. `PUBLICATION_APPROVED`

Do not use `finished`, `complete`, or `publication-ready` as filename-driven states. A document may contain 48 sections and still remain a draft or failed candidate.

## 5. Required authoritative source freeze

Before writing, create `SOURCE_REGISTER.tsv` with:

- source path or portable locator;
- source role;
- byte count;
- SHA-256;
- profile/run/database version;
- acquisition/computation date;
- exact-locus binding method;
- admission state;
- limitations.

At minimum inspect and account for:

1. exact antiSMASH region GBK and source ZIP;
2. Mamey manifest and exact crosswalk;
3. Mamey CDS, domain, HMM, motif, module, and substrate tables;
4. nr BLASTP;
5. ClusteredNR BLASTP, kept separate from nr;
6. Swiss-Prot BLASTP;
7. EBI/UniProt if available, kept as its own channel;
8. MIBiG convergence and per-gene tables;
9. BiG-SCAPE database/run/cutoff record;
10. ClusterBlast/KnownClusterBlast;
11. RG-GMCI;
12. chitin census;
13. resistance/self-resistance screens;
14. domain/motif rarity;
15. literature and gene-family cards;
16. cohort prevalence;
17. predecessor Mode B card(s);
18. an earlier evidence chapter and locus map or data for this locus;
19. reference-strain comparisons;
20. assay, metabolomics, expression, or culture evidence if present.

If a stream does not exist or cannot be exact-bound, record its state. Do not omit its row.

## 6. Exact-locus binding gate

The primary identity tuple is:

`strain | assembly hash | full node/contig | antiSMASH region or interval | sequence hash | CDS roster`

The writer and auditor must establish:

- exact region start/end;
- contig length and edge/interior state;
- raw CDS count;
- exact-region CDS count;
- boundary-context CDS count;
- excluded or quarantined CDS;
- region key when available;
- source-local aliases for provenance only;
- whether loose and relaxed captures have different intervals or denominators.

Any mismatch becomes a typed hold. Never repair identity by joining on the BGC number alone.

## 7. Evidence-retention ledger

Create `EVIDENCE_RETENTION_LEDGER.tsv` before drafting. Required columns:

`evidence_element_id, evidence_stream, predecessor_locator, current_source_locator, exact_binding, predecessor_value, current_value, disposition, reason, card_section, claim_ceiling, auditor_state`

Allowed dispositions:

- `RETAINED_UNCHANGED`
- `RETAINED_SOURCE_QUALIFIED`
- `CORRECTED_WITH_EVIDENCE`
- `SUPERSEDED_BY_NEWER_BOUND_SOURCE`
- `QUARANTINED_UNRELIABLE_OR_UNBOUND`
- `NOT_APPLICABLE_WITH_REASON`
- `MISSING_RECOVERY_REQUIRED`
- `PENDING_EXACT_BOUND_IMPORT`

The ledger must account for all predecessor tables, citations, quantitative measurements, overlays, figures/data pointers, and conclusions. "The new card is shorter" is a warning that requires an explicit retention audit.

## 8. Mandatory per-gene table

Every displayed gene must appear. Boundary-context genes must be marked and excluded from exact denominators.

Required columns:

1. strain/full node/region/BGC display;
2. locus tag;
3. exact-region or boundary-context membership;
4. coordinates and strand;
5. nucleotide and amino-acid lengths;
6. antiSMASH product/function annotation;
7. domain/HMM/module evidence;
8. proposed bounded role;
9. database channel;
10. matched accession;
11. complete matched protein name;
12. matched organism;
13. percent identity;
14. percent positives/similarity;
15. aligned amino acids;
16. query coverage;
17. coverage basis;
18. E-value;
19. bitscore;
20. hit rank;
21. evidence/admission state;
22. caution or reconciliation note.

Use one gene × channel row when space permits. nr, ClusteredNR, Swiss-Prot, and EBI/UniProt may never be merged into one percentage. A blank value is `NR` or a typed missing state, never zero. The match target must always accompany its percentages.

## 9. Required evidence-stream treatment

### antiSMASH

Report exact interval, boundary, product calls, protocluster count/geometry, domains, modules, motifs, and source profile. Detection calls are capacity hypotheses. Overlapping protoclusters are not accepted product counts.

### Mamey

Use the sealed package manifest, crosswalk, CDS/domain/module/HMM/motif outputs, MIBiG, ClusterBlast, RG-GMCI, resistance, and provenance tables. Report target-bound row counts. Treat scores as deterministic routing priors, not biological judgments.

### MIBiG/KCB

Retain the full comparator set or provide a complete appendix. Report accession, reference compound label, distinct query genes, identity, coverage, QC flags, class concordance, and tier. A compound label belongs to the reference record, not automatically to this locus.

### BiG-SCAPE

Report database/run ID, cutoff, exact record ID, family ID, cohort/reference composition, duplicate/relabeling controls, and whether placement is run-relative. Singleton/private does not equal chemical novelty.

### ClusterBlast

Retain per-gene rows or a complete machine-readable companion. Report reference accession, identity, coverage, rank, and source type. Taxonomic labels do not prove organism identity or HGT.

### RG-GMCI

Display every partner locus as strain/full node/region/local alias. Report score, evidence base, reference geometry, functional-rescue class, tiling verdict, and guard. It is homology-guided linkage, not nucleotide joining.

### Chitin

Separate strain-level chitin capacity from exact-locus intersection. Report the exact intersection count. Zero intersection means no bound locus evidence, not no strain-level relevance.

### Resistance

Distinguish transporter-only routing, target-modification candidates, resistant-target evidence, and phenotype. Co-location is not self-resistance.

### Domain rarity

Report the governed denominator, filtered families, exact genes, rarity threshold, and source bridge. Rare-domain status is not scaffold novelty.

### Literature

Retain primary pathway, class-level, and gene-specific citations. Separate what the reference study demonstrated from what similarity suggests for this locus. Never transfer exemplar activity or structure.

### Prevalence

Report the exact dated denominator and unit: genes, loci/cards, strains, or events. Never merge them. Historical measurements must be labeled historical unless recomputed against the current governed cohort.

### Earlier cards and evidence chapters

Preserve valuable measurements, tables, citations, and comparator logic. Correct stale denominators and overstrong conclusions explicitly. Preserve old bytes; do not overwrite.

### Reference strains

Use reference strains when exact records are available. Report assembly/accession, node/region/interval, sequence identity, alignment coverage, synteny, missing segments, and source receipt. If the panel is still being built, use `PENDING_EXACT_BOUND_IMPORT`; do not infer absence.

## 10. The 48-section writing contract (full48 profile)

A full48 card must contain §§1–48 exactly once and in order. Each section must be substantive, locus-specific, and source-aware. Drafts can record `Not applicable`, `not measured` or `pending` with reasons and next evidence. `Pending` is not terminal closure for a selected finished-current-evidence profile; apply its ratified readiness, matrix and independent review requirements.

Copy the section titles exactly from the template that `emit-modeb-template` writes. Do not retype them from memory or from another document: the verifier compares each title, including spelling (for example "judgement") and punctuation, and reports `TITLE_MISMATCH` when one differs. The profile matrix shows how to read the emitted titles.

Appendices may follow §48 but may not create duplicate `## §N` headings.

## 11. Scientific-writing rules

- Lead with the most defensible interpretation.
- Describe architecture before naming a product family.
- Name exact genes supporting each core, tailoring, transport, and regulatory hypothesis.
- Explain alternatives and contradiction resolution.
- Use `family resemblance`, `capacity`, `candidate component`, and `planning lead` where appropriate.
- Never describe a top hit as characterization.
- Never describe a BiG-SCAPE private family as novel chemistry.
- Never describe strain activity as locus-attributed without a binding bridge.
- Never describe RG-GMCI as physical joining.
- Make missing evidence visible without equating it to biological absence.

### 11.1 Gene-or-typed-none reader orientation

Every section that discusses a protein family, enzyme, domain, transporter,
resistance candidate, regulator, tailoring function, core function or
comparator must orient the reader to the exact genes on first use. Do not write
"the APH-family protein," "the ABC systems," "the regulator," or equivalent
collective prose without locus tags in the same paragraph or immediately
following table.

If a searched stream contains zero exact-bound candidates, use the typed form:

`ZERO_EXACT_BOUND_CANDIDATES; denominator=<N> exact displayed proteins; sources=<source list>`

The denominator must equal the independently supplied displayed-protein roster.
This state means no candidate was found in the measured scope; it is not a claim
of biological absence. Card length is not a target. A concise exact-gene
statement passes; long family-only prose fails.

### 11.2 Section 27 self-resistance contract

Positive candidates require this exact subsection and table:

#### Candidate gene orientation

| Gene | Physical membership | Candidate role | Evidence source | Class concordance | Allowed inference |
|---|---|---|---|---|---|

Allowed physical-membership states are `EXACT_REGION`, `BOUNDARY_CONTEXT`, and
`OUTSIDE_EXACT_REGION_QUARANTINED`. Allowed class-concordance states are
`CONCORDANT`, `DISCORDANT`, `UNRESOLVED`, and `NOT_APPLICABLE`. Every exact gene
mentioned anywhere in Section 27 must occur in the table. The section must end
with `#### Claim ceiling`. A transporter or resistance-like fold is not producer
protection without gene-specific mechanism and compound-class concordance.

If no candidate is found, use the validated zero-candidate state and still give
the claim ceiling. Do not substitute a generic "self-resistance is not
assigned" paragraph for the searched genes and denominator.

### 11.3 Section 45 cohort gene-comparison contract

This subsection uses full48 numbering. In `current50_v2`, §45 is the optional "Supervisor / university
cohort comparison" section with its own requirement in `mamey/data/mode_b/modeb_current50_v2_contract.json`.
Apply the rules below to a `current50_v2` card only where it reports a cohort gene comparison.

Predecessor preservation, earlier ranking, authoring history and source-loss accounting
belong in the provenance ledger; they do not satisfy cohort comparison. Section
45 requires:

1. `#### Cohort comparison denominator`, defining the strain and locus scope.
2. `#### Cohort gene comparison`, with the exact columns below.
3. `#### Cohort-comparison conclusion`, stating the bounded inference.

| Comparator exact locus | Query genes | Comparator genes | Sequence / synteny evidence | Agreement and mismatch | Allowed inference |
|---|---|---|---|---|---|

Every comparator must display `strain / full node-or-contig / region / BGC
alias`. Query and comparator genes must be named explicitly. A family label,
aggregate score or strain name without genes is insufficient.

If the comparison source is genuinely unavailable, use:

`COHORT_COMPARISON_NOT_AVAILABLE_TYPED; denominator=<searched scope>; sources=<source list>; reason=<why no comparison can be reported>`

This unavailable state is not permitted when an accessible bound cohort source
already contains the requested comparison.

### 11.4 Anti-padding rule

Do not expand prose to meet a word or character target. The full48 publication gate has a heuristic
check for long generic sentences repeated across three or more sections, with exclusions for evidence
markers and some document structures. It does not establish that all remaining prose is substantive,
and the current50 v2 path does not invoke that full48 publication check. Replace repetition with exact
genes, measurements, source states, agreement/mismatch analysis or a typed evidence-absence state.
A shorter dense card is preferable to a longer padded card.

## 12. Writer deliverables

For each card, the writer produces the files below. This is a hand-made convention; no Mamey command writes them. Add new versions; do not overwrite old ones.



- `...__ModeB_CARD__EVIDENCE_RECONCILED_CANDIDATE_vN.md`
- `EVIDENCE_RETENTION_LEDGER.tsv`
- `SOURCE_REGISTER.tsv`
- `GENE_CHANNEL_EVIDENCE.tsv` if the full table is not only inline
- `DIFFERENCE_REPORT.md`
- `QA_RECEIPT.json`
- `CURRENT_STATE.json`
- `EXPLORATION_JOURNAL.tsv`
- `CHECKPOINTS.tsv`
- `DECISION_AND_HOLD_LEDGER.tsv`
- `ARTIFACT_MANIFEST.tsv`
- `SAVE_STATE.md`

No predecessor is overwritten. Rendering is deferred until the project owner explicitly authorizes it.

## 13. Auditor acceptance tests

The auditor must fail the candidate if any condition below is false:

1. exact identity resolves one-to-one;
2. sections 1–48 (full48) appear exactly once and in order;
3. all predecessor locus tags are accounted for;
4. exact and context denominators are explicit;
5. every displayed gene has all expected channel states;
6. identity and positives/similarity are separate;
7. every percentage names its channel, accession, protein, and organism;
8. aligned length, query coverage, coverage basis, E-value, bitscore, and evidence state are retained or explicitly unavailable;
9. all required evidence streams have ledger dispositions;
10. all predecessor citations and comparator records are retained, superseded with reason, or quarantined;
11. Mamey aliases are crosswalked rather than transferred;
12. every other locus is displayed with strain/full node/region/BGC or qualified local alias;
13. run-relative BiG-SCAPE and RG-GMCI guards are present;
14. no product, activity, novelty, ecology, HGT, resistance, or physical-linkage claim exceeds evidence;
15. source hashes and artifact-manifest hashes validate;
16. the document state is not falsely labeled finished or publication-ready;
17. unresolved reference work is `PENDING`, not interpreted as negative;
18. no rendering occurred without the project owner's green light.

The auditor reports each check as `PASS`, `FAIL`, or `HOLD` with evidence and line/file locator. A failed card remains preserved as an unaccepted candidate.

## 14. Difference report contract

The writer must state:

- material retained from the predecessor;
- material added from newer sources;
- numerical values corrected;
- claims weakened or withdrawn;
- content quarantined and why;
- evidence still pending;
- anything present in the predecessor but absent from the candidate.

The final line must be either:

`ZERO_UNEXPLAINED_PREDECESSOR_OMISSIONS`

or

`UNEXPLAINED_OMISSIONS_REMAIN — CANDIDATE_FAIL`

## 15. Feedback loop

Feedback is welcome but not required for progress.

1. Writer seals a candidate and evidence ledger.
2. Auditor produces an additive findings file.
3. Writer answers each finding in a disposition table.
4. Auditor rechecks only changed and dependent claims plus global invariants.
5. the project owner accepts, rejects, or requests another pass.

Do not silently edit another system's accepted source. Use additive versions and supersession pointers.

## 16. Scaling rule

Do not scale based on one polished card. First pass two deliberately difficult pilots with zero unexplained omissions. Only then convert the contract into automation. Automated generation must still preserve one-card-at-a-time exact-locus ledgers and permit independent content audit.

## 17. Recovery pilot pattern

Before scaling, run the protocol on a deliberately difficult locus and check that it keeps these distinctions:

- exact-region CDS versus boundary-context CDS;
- the frozen identity versus a qualified local identity from a loose or relaxed run;
- a bounded subsystem versus a broader multi-system region;
- retained historical measurements versus current source-state limits;
- strain-level capacity versus exact-locus intersection;
- routing evidence versus accepted physical linkage;
- historical prevalence versus current recomputation.

Reuse the protocol and schemas only. Never carry one locus's biological conclusions to another.

## 18. Compact assignment text for a writer or auditor

> Act as the Mode B writer for one exact locus. Use `strain / full node-or-contig / antiSMASH region / BGC alias` everywhere. Freeze and hash the exact GBK, Mamey package, BLASTP channels, MIBiG, BiG-SCAPE, ClusterBlast, RG-GMCI, chitin, resistance, domain rarity, literature, prevalence, earlier Mode B cards and evidence chapters, and reference-strain evidence. Build an evidence-retention ledger before prose. Write the profile's sections (§§1–48 for full48) exactly once and include the complete gene × channel table with matched accession/protein/organism, identity, positives, aligned length, query coverage, coverage basis, E-value, bitscore, and evidence state. Every predecessor element must be retained, corrected, superseded, quarantined, not-applicable, or missing with reason. Do not call the result finished or publication-ready. Preserve predecessors and issue an evidence-reconciled candidate plus source register, difference report, QA receipt, durable state, and manifest. Do not render without the project owner's authorization.

> Act as the independent Mode B auditor for one candidate. Re-resolve exact identity and denominator from sources. Compare predecessor, candidate, evidence-retention ledger, and every supporting stream. Fail any unexplained omission, alias-only join, missing gene/channel row, unnamed percentage match, conflated BLASTP channel, unsupported product/activity/novelty/HGT/resistance/linkage claim, stale prevalence presented as current, missing source hash, or false completion label. Produce additive findings with file/line evidence. Do not rewrite or accept the candidate; the project owner owns acceptance.

## 19. Claim ceiling

All outputs remain class- and component-capacity hypotheses unless stronger exact-locus evidence is explicitly admitted. Similarity is not identity; capacity is not production; missing or unbound evidence is not biological absence. Scientific acceptance, integration, release, and publication are separate owner gates.
