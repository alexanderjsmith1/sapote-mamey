# Mode B dual-writer / dual-auditor evidence-retention protocol

**Date:** 2026-08-20
**Audience:** Claude and Codex
**Purpose:** enable either system to write Mode B cards and either system to audit them without allowing polished prose, filenames, section counts, or self-certification to substitute for evidence completeness.
**Immediate lesson:** a 48-section card can still be materially incomplete. The predecessor-to-successor evidence-retention audit is a mandatory gate.

*(Relayed verbatim by the Developer or User, 2026-08-20, into the .372 patch queue. Staged by the patch lane; see
PATCH_CARD.md for the review notes and the FINISHED_CURRENT_EVIDENCE trigger-token conflict.)*

## 1. Controlling principles

1. Similarity is not identity.
2. Capacity is not expression, production, activity, or ecological function.
3. Missing, unbound, or un-ingested evidence is not biological absence.
4. Exact assembly + full node/contig + antiSMASH region/interval + sequence/CDS roster controls identity. A BGC alias is display metadata, never a sufficient join key.
5. Every predecessor evidence element must receive an explicit disposition. It may be retained, corrected, superseded, quarantined, declared not applicable, or declared missing. It may not silently disappear.
6. A writer cannot establish publication readiness by completing §§1–48. An independent audit must first demonstrate evidence retention, exact-source binding, and claim safety.
7. Mamey is deterministic extraction and routing evidence. It informs writing but does not supply product, activity, novelty, merge, or publication judgment.
8. Historical material remains evidence even when its interpretation is superseded. Preserve source bytes and separate useful measurements from stale conclusions.
9. Reference comparisons must identify the reference assembly/record and report identity, coverage, synteny, and source provenance. Host category or compound label alone is not a comparison.
10. the Developer or User alone accepts a card, authorizes scaling, approves rendering, and determines release/publication status.

## 2. Mandatory display and folder identity

Every deliverable, table, heading, filename, message, ledger, and review note referring to an AS locus must use:

`strain / full node-or-contig / antiSMASH region / BGC alias`

Example:

`AS-XXX / NODE_4_length_335315_cov_71.173128 / region002 / BGC028`

Never write `BGC028` by itself when referring to an AS locus. MIBiG accession identifiers such as `BGC0002676.2` are reference-record identifiers and must be labeled as MIBiG accessions.

Recommended folder name:

`<strain>__<full_node_or_contig>__<region>__<BGC_alias>/`

Loose and relaxed antiSMASH runs may renumber aliases. Preserve these only as qualified local aliases, for example:

`AS-XXX / NODE_4_length_335315_cov_71.173128 / region002 / loose-package local alias BGC037`

Never transfer a local alias to the frozen card identity. Crosswalk on the full node, region interval, sequence hash, and CDS roster. Quarantine ambiguity.

## 3. Dual-role operating model

Claude and Codex may each serve as writer or auditor. Assign roles per card, not permanently.

### Writer responsibilities

The writer:

1. freezes and hashes authoritative inputs;
2. establishes exact locus identity and denominator;
3. creates the evidence-retention ledger before prose;
4. extracts every admitted evidence stream;
5. writes the ordered §§1–48 card;
6. includes the complete per-gene evidence table;
7. declares corrections, supersessions, quarantines, and missing evidence;
8. issues a candidate receipt without claiming independent acceptance.

### Auditor responsibilities

The auditor independently:

1. re-resolves the exact locus from sources;
2. checks hashes, source locators, and denominator;
3. compares predecessor, candidate, and source evidence;
4. verifies every retention-ledger disposition;
5. confirms all §§1–48 are substantive and correctly ordered;
6. checks every gene and every BLASTP channel row;
7. challenges product, activity, novelty, ecology, HGT, resistance, prevalence, and cross-contig claims;
8. issues findings without silently rewriting the writer's candidate.

### Independence rule

The same writing pass may run mechanical self-checks, but it may not self-certify `CONTENT_QA_PASSED`, `MAINTAINER_ACCEPTED`, or publication readiness. A second system, a separate saved task, or a later independent pass must audit it. The auditor reports evidence; the Developer or User decides acceptance.

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
18. V7 evidence chapter and locus map/data;
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

Retain the full comparator set or provide a complete appendix. Report accession, reference compound label, distinct query genes, identity, coverage, QC flags, class concordance, and tier. A compound label belongs to the reference record, not automatically to the AS locus.

### BiG-SCAPE

Report database/run ID, cutoff, exact record ID, family ID, cohort/reference composition, duplicate/relabeling controls, and whether placement is run-relative. Singleton/private does not equal chemical novelty.

### ClusterBlast

Retain per-gene rows or a complete machine-readable companion. Report reference accession, identity, coverage, rank, and source type. Taxonomic labels do not prove organism identity or HGT.

### RG-GMCI

Display every AS partner as strain/full node/region/local alias. Report score, evidence base, reference geometry, functional-rescue class, tiling verdict, and guard. It is homology-guided linkage, not nucleotide joining.

### Chitin

Separate strain-level chitin capacity from exact-locus intersection. Report the exact intersection count. Zero intersection means no bound locus evidence, not no strain-level relevance.

### Resistance

Distinguish transporter-only routing, target-modification candidates, resistant-target evidence, and phenotype. Co-location is not self-resistance.

### Domain rarity

Report the governed denominator, filtered families, exact genes, rarity threshold, and source bridge. Rare-domain status is not scaffold novelty.

### Literature

Retain primary pathway, class-level, and gene-specific citations. Separate what the reference study demonstrated from what similarity suggests for the AS locus. Never transfer exemplar activity or structure.

### Prevalence

Report the exact dated denominator and unit: genes, loci/cards, strains, or events. Never merge them. Historical measurements must be labeled historical unless recomputed against the current governed cohort.

### Historical Mode B and V7

Preserve valuable measurements, tables, citations, and comparator logic. Correct stale denominators and overstrong conclusions explicitly. Preserve old bytes; do not overwrite.

### Reference strains

Use reference strains when exact records are available. Report assembly/accession, node/region/interval, sequence identity, alignment coverage, synteny, missing segments, and source receipt. If the panel is still being built, use `PENDING_EXACT_BOUND_IMPORT`; do not infer absence.

## 10. The 48-section writing contract

The card must contain §§1–48 exactly once and in order. Each section must be substantive, locus-specific, and source-aware. `Not applicable`, `not measured`, and `pending` are allowed only with reasons and next evidence.

The required section names are:

1. Identity and node/region
2. Why this BGC was selected
3. Boundary and assembly status
4. Gene-by-gene interpretation
5. Core biosynthetic logic
6. Tailoring and maturation logic
7. Transport, resistance, and regulation
8. Comparator/KCB interpretation
9. Alternative hypotheses
10. Fragmentation and co-capture risks
11. Product-family interpretation
12. Host/microbe ecological interpretation
13. Antibacterial/antifungal relevance
14. What cannot be claimed
15. Missing evidence
16. BLASTP/HMMER next steps
17. LC-MS/fermentation implications
18. Figure/locus-map notes
19. Final Mode B judgment
20. Next actions
21. Precursor mass ladder
22. RiPP database search
23. Heterologous expression
24. Scaffold novelty score
25. Genome neighborhood
26. OSMAC protocol
27. Self-resistance assessment
28. Evidence provenance ledger
29. Cross-cluster interactions
30. Experimental decision tree
31. Region CDS census
32. Assembly-line inventory
33. Module programming readout
34. Initiation and release logic
35. Protocluster decomposition
36. Boundary/overmerge/locus-splitting adjudication
37. Partner and accessory proteins
38. Co-located resistance and efflux
39. Cross-strain sequence identity
40. BiG-SCAPE family/cohort placement
41. Protein/domain phylogeny
42. Horizontal-transfer evidence
43. Split-pathway/cross-contig RG-GMCI
44. Within-cohort prevalence and tier
45. Supervisor/university cohort comparison
46. Type/reference-strain comparison
47. Host-matched unrelated reference
48. Cross-cohort synthesis and claim ceiling

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

Predecessor preservation, V7 rank, authoring history and source-loss accounting
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

Do not expand prose to meet a word or character target. The publication gate
rejects the same evidence-free sentence repeated across three or more sections.
Replace repeated conclusions with exact genes, measurements, source states,
agreement/mismatch analysis or a typed evidence-absence state. A shorter dense
card is preferable to a longer padded card.

## 12. Writer deliverables

For each card, the writer produces additively:

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

No predecessor is overwritten. Rendering is deferred until the Developer or User explicitly authorizes it.

## 13. Auditor acceptance tests

The auditor must fail the candidate if any condition below is false:

1. exact identity resolves one-to-one;
2. sections 1–48 appear exactly once and in order;
3. all predecessor locus tags are accounted for;
4. exact and context denominators are explicit;
5. every displayed gene has all expected channel states;
6. identity and positives/similarity are separate;
7. every percentage names its channel, accession, protein, and organism;
8. aligned length, query coverage, coverage basis, E-value, bitscore, and evidence state are retained or explicitly unavailable;
9. all required evidence streams have ledger dispositions;
10. all predecessor citations and comparator records are retained, superseded with reason, or quarantined;
11. Mamey aliases are crosswalked rather than transferred;
12. every other AS locus is displayed with strain/full node/region/BGC or qualified local alias;
13. run-relative BiG-SCAPE and RG-GMCI guards are present;
14. no product, activity, novelty, ecology, HGT, resistance, or physical-linkage claim exceeds evidence;
15. source hashes and artifact-manifest hashes validate;
16. the document state is not falsely labeled finished or publication-ready;
17. unresolved reference work is `PENDING`, not interpreted as negative;
18. no rendering occurred without the Developer or User's green light.

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
5. the Developer or User accepts, rejects, or requests another pass.

Do not silently edit another system's accepted source. Use additive versions and supersession pointers.

## 16. Scaling rule

Do not scale based on one polished card. First pass two deliberately difficult pilots with zero unexplained omissions. Only then convert the contract into automation. Automated generation must still preserve one-card-at-a-time exact-locus ledgers and permit independent content audit.

## 17. Immediate pilot

The current recovery pilot is:

`AS-XXX / NODE_4_length_335315_cov_71.173128 / region002 / BGC028`

It demonstrates the required distinction between:

- 90 exact-region CDS and one boundary-context CDS;
- frozen display alias BGC028 and loose-package local alias BGC037;
- a bounded skyllamycin/WS9326-like subsystem and a broader multi-system region;
- retained historical BLASTP measurements and current source-state limitations;
- strain-level chitin capacity and zero exact-locus chitin intersection;
- Mamey/RG-GMCI routing and accepted physical linkage;
- historical prevalence and current recomputation.

The example's biological conclusions must not be transferred to other loci. Reuse only the protocol and schemas.

## 18. Compact assignment text for Claude or Codex

> Act as the Mode B writer for one exact locus. Use `strain / full node-or-contig / antiSMASH region / BGC alias` everywhere. Freeze and hash the exact GBK, Mamey package, BLASTP channels, MIBiG, BiG-SCAPE, ClusterBlast, RG-GMCI, chitin, resistance, domain rarity, literature, prevalence, historical Mode B, V7, and reference-strain evidence. Build an evidence-retention ledger before prose. Write §§1–48 exactly once and include the complete gene × channel table with matched accession/protein/organism, identity, positives, aligned length, query coverage, coverage basis, E-value, bitscore, and evidence state. Every predecessor element must be retained, corrected, superseded, quarantined, not-applicable, or missing with reason. Do not call the result finished or publication-ready. Preserve predecessors and issue an evidence-reconciled candidate plus source register, difference report, QA receipt, durable state, and manifest. Do not render without the Developer or User's authorization.

> Act as the independent Mode B auditor for one candidate. Re-resolve exact identity and denominator from sources. Compare predecessor, candidate, evidence-retention ledger, and every supporting stream. Fail any unexplained omission, alias-only join, missing gene/channel row, unnamed percentage match, conflated BLASTP channel, unsupported product/activity/novelty/HGT/resistance/linkage claim, stale prevalence presented as current, missing source hash, or false completion label. Produce additive findings with file/line evidence. Do not rewrite or accept the candidate; the Developer or User owns acceptance.

## 19. Claim ceiling

All outputs remain class- and component-capacity hypotheses unless stronger exact-locus evidence is explicitly admitted. Similarity is not identity; capacity is not production; missing or unbound evidence is not biological absence. Scientific acceptance, integration, release, and publication are separate owner gates.
