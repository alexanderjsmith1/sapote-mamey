<!-- Mirror of docs/GLOSSARY.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
<!-- CANONICAL GLOSSARY -->
# Sapote-Mamey glossary

Find a term from a result, report or command. Search this page with **Ctrl+F**
(**Command+F** on Mac), or start with the core concepts below. Workbook cell codes
have their own [cell-status glossary](../docs/troubleshooting/CELL_STATUS_CODE_GLOSSARY.md).

This is the canonical glossary. Formulas and thresholds describe the named
implementation; check that source when comparing results from different builds.
## Running and reading a run

These terms appear in the terminal and in the first-run steps. The
[first-run page](../docs/reader/01_FIRST_RUN.md) walks through them in order.

| Term | Meaning |
|---|---|
| Package | The folder `run` writes for one strain, for example `runs/EXAMPLE/package/`. It holds the inventory, boards, workbook, issue log, receipts and `manifest.json`. |
| Workbook | The Excel file in the package, `EXAMPLE_5_workbook.xlsx`. It collects the inventory and boards on separate sheets. |
| Issue log | `issue_log.md` in the package. It lists the issues the run recorded, one line each. A line starting `- [BLOCKING]` is a blocking problem. Other lines are warnings, and `- No blocking issues recorded.` is the summary when there is nothing to report. See [recovery](../docs/reader/04_RECOVERY_AND_LIMITS.md#find-what-failed). |
| Gold (`--mode gold`) | The analysis mode of `run`. Use it for real analysis. |
| Capped session (`--capped-session`) | A lighter run for a session with a time limit. It cannot promise to finish before the limit. It requires the workbook, forces `--brief none` and `--json-evidence off`, and turns off automatic gene maps unless you set a map option. Without the cap, `run --json-evidence` defaults to `bounded`. A separate step still reads the JSON for the KCB percent and TIGRFAM hits; if those values are missing, check that step's status. See [JSON evidence modes](../docs/reader/04_RECOVERY_AND_LIMITS.md#json-evidence-modes). |
| Seal | The final integrity step on a package (`seal-package`). It runs the quality checks and writes a receipt with checksums. See also **Sealed package** below. |
| `MAMEY_COMPLETE` | The run finished and the package passed the extraction checks. `MAMEY_COMPLETE_WITH_ISSUES` means it finished and recorded issues; an optional step may have failed or skipped an output, so read the issue log. Neither means the biology was reviewed. |
| Exit code of `run` | `0` finished. `1` not usable: a `[BLOCKING]` issue, a placeholder refusal, a locked output folder, or an error. `2` refused before any work, for a bad command line. See [recovery](../docs/reader/04_RECOVERY_AND_LIMITS.md). |

`package_status.json` holds three status fields: `terminal_status` (how the run ended),
`validator_status` (the last `validate`) and `package_status` (the recovery state).
`package_status` has four values:

| `package_status` value | Meaning |
|---|---|
| `MAMEY_COMPLETE` | A normal run, including one that recorded issues. It is not proof of complete extraction; read the terminal status and the newest validation. |
| `RECOVERY_VALIDATED` | The package holds a validated-recovery marker file. It was recovered, not run straight through. |
| `RECOVERY_NEEDED` | The package holds a recovery-needed marker, or another file with "recovery" in its name. Recover it or review it by hand. |
| `PARTIAL_FAILED` | The newest validation failed, or the recorded status is not a recognized success. A failed fresh validation wins over every other value. |

`run_phase_receipts.jsonl` records each step's `START`, `END`, `ERROR`, `FAIL`, `TIMEOUT`,
`SKIP` or `WARN`. The run writes it as it goes, so a crash can leave the last line missing.
[Recovery](../docs/reader/04_RECOVERY_AND_LIMITS.md#find-what-failed) explains each status.

Other status words in the terminal come from the command that prints them. Copy the
printed code. `INPUT_MISSING` means a required input file is absent. `MAMEY_FAILED`
means the deterministic scan failed, with a reason. `UNSUPPORTED_ACCESSION_MODE` means
an accession-only run was requested; supply an antiSMASH ZIP instead. `DEFERRED` is a
work decision, not an engine status.

## Files and names used at the front door

| Term | Meaning |
|---|---|
| FASTA / FASTQ | Text formats for sequences. FASTA holds named sequences; FASTQ also holds per-base quality values. A raw genome FASTA is not an antiSMASH result ZIP. |
| GenBank / GBK | A sequence-record format that can include features and their locations. A region GBK is one kind of file in an antiSMASH result. |
| Contig | A contiguous assembled sequence. A genome assembly can contain many contigs; separate contigs are not automatically physically joined by a prediction. |
| Protocluster | An antiSMASH prediction of a biosynthetic unit inside a called region. One region can contain more than one protocluster; that count alone does not prove distinct products. |
| CSV / TSV / JSON | Text formats for tables or structured data. CSV uses comma-separated fields, TSV uses tabs, and JSON represents structured values. Open these without changing the originals. |
| ZIP | An archive containing files. The antiSMASH result ZIP is an input; a completed Mamey package ZIP is an output. |
| HTML / PDF | Document formats: HTML is typically opened in a web browser; PDF preserves a page layout. Links and their destinations can depend on where files are stored. |
| PNG / SVG | Image formats. PNG stores pixels; SVG uses vector graphics. Check the figure and its source data before using either in a report. |
| DOI | A persistent identifier for a published work or other research object. Check that the linked record matches the work being cited. |
| `HANDBACK.json` | A pointer to the newest completed package ZIP in a run output folder. A later run can replace the pointer, so retain the actual ZIP and its provenance. |
| GECCO | An optional independent BGC-prediction tool whose results can be compared with antiSMASH predictions. Agreement or disagreement alone does not establish a compound or activity. See [companion evidence](../docs/COMPANION_CLASS_EVIDENCE.md). |
| antiSMASH | Software that predicts biosynthetic regions and annotates their sequence context. Mamey reads its supplied result files; an annotation is a computational prediction. |
| BLASTp | A protein-sequence similarity search. Interpret a hit with its alignment, coverage and source context; similarity alone does not prove function. |
| ANI / dDDH | Average nucleotide identity and digital DNA-DNA hybridization are genome-comparison measures. Record the comparison genome and method; neither reports a compound or activity. |
| rDNA / ITS | Ribosomal DNA includes rRNA genes; an internal transcribed spacer is a marker region between rRNA genes. Marker similarity is sequence context, not an automatic species identification. |
| Evidence conservation / reconciliation | Compare a reported value, identity or claim with its bound source, or compare the same value across named routes. A mismatch needs investigation; a pass covers only the fields checked. |
| Genome-grounded / proteome-scope-gated | A capacity claim needs admitted genomic evidence, and its conclusion must respect what was searched. A region-only scan cannot establish absence across a whole proteome. |
| Chemotype | A chemical or biosynthetic class inferred from the features and rules named by an analysis. A class annotation does not identify a final molecule. |
| PTM / HSAF | In the class framework, PTM means polycyclic tetramate macrolactam; HSAF is one characterized reference product. PTM can also mean post-translational modification in other contexts. A class trigger does not establish HSAF production. |
| HMMER | Software for searching with profile hidden Markov models. Interpret a match with its model, thresholds and source context. |
| Isolation source | The material or setting recorded for an isolate. Preserve the source record and uncertainty; a label alone does not establish a host relationship or an activity. |
| Observed / computed / inferred / assumed | Observed is present in a named source; computed comes from a stated rule; inferred interprets evidence; assumed is used without confirmation. An observed annotation may itself be a prediction. |
| Re-scoring | Applying a stated scoring implementation to records again. Compare runs only with compatible engines, configuration and evidence; re-scoring cannot repair differences in sampling or assays. |
| PKS / NRPS domains | KS extends a PKS chain, AT selects an acyl unit, and ACP carries the chain; KR, DH and ER affect reduction, and TE can release or cyclize. In NRPS, A selects and activates a substrate, T/PCP carries it, C joins units, and E can change stereochemistry. Domain annotation supports a capacity hypothesis, not a confirmed final product. |
| Halogenase | An enzyme that can add a halogen to a substrate. A predicted halogenase does not identify the modified substrate or establish an activity. |
| Self-resistance / resistance-directed mining | Self-resistance is a producer's protection against its own product. Resistance-directed mining uses resistance-associated genes to flag candidates; a nearby annotation alone does not establish self-resistance or production. |
| Taxonomy / accession | Taxonomy names a classification; an accession identifies a database record. Keep the recorded assignment, record and verification state separate. |
| `FORMAT_ONLY` | A workbook BGC-ID check used the ID's form rather than membership in the package inventory. A well-formed ID from another package can pass. |
| `package_status_receipt_write: FAILED` | Validation ran but could not save its status receipt. Read the printed validation result and resolve the write problem. |
| Homology / phylogeny | Homology is shared ancestry; a phylogeny is a hypothesis of evolutionary relationships built using stated data and methods. Similarity alone does not establish either the cause or the full history. |
| Research cohort | The selected set of samples or strains in an analysis; report its membership and exclusions. This is distinct from a release tier also named COHORT. |
| Heatmap / figure series F, G, D | A heatmap uses color for values in a grid. In the cohort catalog, F names heatmap panels, G complementary panels, and D dot or bubble panels; check each panel's data and legend. |
| Primary metabolism / mobile element | Primary metabolism supports basic cellular functions; mobile genetic elements can move or be transferred. A selected workflow may filter their annotations from lead displays; inspect the actual rule and scope. |
| `ijson` | A core dependency and streaming JSON parser used by the bounded main evidence reader. If unavailable, that reader falls back to off; the separate record pass has its own status. |
| SQLite | A database format stored in a file. A workflow's database can hold multiple runs; select the intended run before interpreting its tables. |
| BiG-SCAPE | Software for comparing and clustering BGCs into gene cluster families under selected settings. Keep the inputs, settings and run identity with the family assignment. |
| Bioassay / mass spectrometry / metabolomics | A bioassay measures a response under stated conditions. Mass spectrometry measures mass-to-charge signals; metabolomics studies molecular features in samples. Link an assay or molecular feature to a BGC only with the required evidence. |
| `two-proof-rescue` | A reader that reassesses candidate RG-GMCI fragment pairs using a second computational channel. Some channels reuse source evidence, so read the receipt and adjudicate rather than treating the name as proof. |
| `PASS_STRUCTURE` | A structural check's pass label. Its meaning depends on the check and does not by itself validate scientific reasoning or citations. |
| `operator_supplied` / `citation_needed` | Citation-provenance labels: one records a value carried from package evidence or comparator fields; the other marks literature support still to be found and checked. Read the corresponding source and status. |
| `JUDGMENT_PENDING` | The gold-completeness check reports that written cards do not cover every region. Some cards can already exist. |
| `VALIDATION_FAIL` | The run's own validation failed and `run` exits 1. Read the named failure and keep the attempt for diagnosis. |
| `PACKAGE_LOCKED` | Another run holds the package lock. Use the recovery instructions rather than overwriting its output. |
| `TAXONOMY_PLACEHOLDER` / `SOURCE_PLACEHOLDER` | A supplied metadata placeholder was refused. Replace it with supported information or omit the field as the run guide allows. |
| Data dictionary | A reference describing fields and their meanings for a named output. Use the dictionary for the specific file and version being read. |
| Expanded-locus evidence | Saved evidence outside a focal region that may be considered in a Mode B card under the selected workflow. Retain the focal identity, source bindings and unresolved fragment relationships. |
| Companion class evidence | Additional class-related evidence from a named companion workflow, such as supplied GECCO predictions. Record its inputs and scope; it does not itself establish a compound or activity. |
| Expression / transcription / translation | Expression describes a gene being used. Transcription produces RNA from DNA; translation produces protein from RNA. Evidence for each step and its conditions must be recorded separately. |
| Alignment / aligned fraction | An alignment arranges sequences for comparison. Aligned fraction states the portion covered under the named comparison's definition; retain the method and denominator. |
| Clade | A group consisting of an inferred common ancestor and its descendants in a tree. Its interpretation depends on the data and tree-building method. |
| Numerator / denominator | The numerator is the counted part of a ratio; the denominator is the stated total or comparison base. Report both and keep missing observations separate. |
| `WORKBOOK_CONTENT` / `BGC_Inventory` | `WORKBOOK_CONTENT` reports the workbook content check. `BGC_Inventory` is the workbook sheet listing the package's BGC inventory. Read the check's status and ID authority. |
| `legacy_alias` | A field reporting that a check accepted an older supported sheet name, such as `Triage_First_Board` for `Triage_Board`. It does not validate other workbook content. |
| `manifest_short.json` | A compact package summary written before final checks. For run status, use the terminal status and newer validation when available. |
| `JSON_EVIDENCE_SKIPPED` | The main JSON walker skipped a file or did not walk JSON; read the issue for its specific reason. The separate record pass has its own status. |
| AAI | Average amino-acid identity, a protein-based genome-comparison measure under a named method and comparison set. It is not an activity measurement. |
| DPI | Dots per inch, a measure of image output resolution. Check the final printed or displayed size as well as the numeric setting. |
| HPLC | High-performance liquid chromatography, a technique that separates components of a sample. Interpret a trace with its sample, detector and method. |
| IQ-TREE | Software for estimating phylogenetic trees. Record the alignment, model, version and support method used for the tree. |
| External tools and reference datasets | Named programs, databases and services in the README's [tool and license table](../README.md#tool-downloads-and-licenses). The table states each one's role and links its source. |
| Bootstrap | The initial steps or generated instructions that prepare a selected workflow. Use the current named bootstrap contract for that workflow. |
| Deterministic extraction | The software applies its stated parsing and scoring rules to supplied inputs under a named implementation and configuration. It does not by itself establish that annotations, joins or conclusions are correct. |
| Fixture | A known input or setup used in a test. A passing fixture test covers its stated case; it is not evidence that every real input succeeds. |
| Renderer | A tool that turns data and drawing instructions into an image or document. Keep the renderer, input data and output checks with the result. |
| Checksum / SHA-256 | A checksum is a value used to compare file content; SHA-256 is one hash algorithm. Matching hashes support byte-level comparison but do not establish scientific correctness. |
| Provenance | The recorded origin and processing history of an item, including its inputs, method and version where available. Preserve the source and any gaps in the record. |
| Checkpoint / transcript | A checkpoint records work state and what to do next; a transcript records the conversation or events it actually covers. A summary is not a verbatim transcript. |

## External tool and reference name index

These names appear in the README catalog. Follow a name to the table for its role, source and terms.

- [Python](../README.md#tool-downloads-and-licenses)
- [antiSMASH](../README.md#tool-downloads-and-licenses)
- [NCBI BLAST+](../README.md#tool-downloads-and-licenses)
- [BiG-SCAPE 2](../README.md#tool-downloads-and-licenses)
- [GECCO](../README.md#tool-downloads-and-licenses)
- [HMMER](../README.md#tool-downloads-and-licenses)
- [clinker](../README.md#tool-downloads-and-licenses)
- [DIAMOND](../README.md#tool-downloads-and-licenses)
- [BLAST+ `tblastn`](../README.md#tool-downloads-and-licenses)
- [GToTree](../README.md#tool-downloads-and-licenses)
- [Barrnap](../README.md#tool-downloads-and-licenses)
- [SeqKit](../README.md#tool-downloads-and-licenses)
- [Prodigal](../README.md#tool-downloads-and-licenses)
- [MUSCLE](../README.md#tool-downloads-and-licenses)
- [MAFFT](../README.md#tool-downloads-and-licenses)
- [trimAl](../README.md#tool-downloads-and-licenses)
- [IQ-TREE 2](../README.md#tool-downloads-and-licenses)
- [FastTree](../README.md#tool-downloads-and-licenses)
- [RAxML-NG](../README.md#tool-downloads-and-licenses)
- [EPA-ng](../README.md#tool-downloads-and-licenses)
- [gappa](../README.md#tool-downloads-and-licenses)
- [FastANI](../README.md#tool-downloads-and-licenses)
- [skani](../README.md#tool-downloads-and-licenses)
- [Pandoc](../README.md#tool-downloads-and-licenses)
- [Cairo](../README.md#tool-downloads-and-licenses)
- [librsvg / rsvg-convert](../README.md#tool-downloads-and-licenses)
- [Inkscape](../README.md#tool-downloads-and-licenses)
- [R](../README.md#tool-downloads-and-licenses)
- [ITSx](../README.md#tool-downloads-and-licenses)
- [BUSCO](../README.md#tool-downloads-and-licenses)
- [compleasm](../README.md#tool-downloads-and-licenses)
- [NCBI Datasets CLI](../README.md#tool-downloads-and-licenses)
- [ggplot2](../README.md#tool-downloads-and-licenses)
- [RDKit](../README.md#tool-downloads-and-licenses)
- [ggtree](../README.md#tool-downloads-and-licenses)
- [patchwork](../README.md#tool-downloads-and-licenses)
- [svglite](../README.md#tool-downloads-and-licenses)
- [Poppler utilities](../README.md#tool-downloads-and-licenses)
- [Google Chrome or Chromium](../README.md#tool-downloads-and-licenses)
- [wkhtmltopdf](../README.md#tool-downloads-and-licenses)
- [Graphviz](../README.md#tool-downloads-and-licenses)
- [IQ-TREE 3](../README.md#tool-downloads-and-licenses)
- [CheckM2](../README.md#tool-downloads-and-licenses)
- [DeepBGC](../README.md#tool-downloads-and-licenses)
- [BiG-SLiCE](../README.md#tool-downloads-and-licenses)
- [cblaster](../README.md#tool-downloads-and-licenses)
- [RiPPER](../README.md#tool-downloads-and-licenses)
- [TriMap](../README.md#tool-downloads-and-licenses)
- [SPAdes](../README.md#tool-downloads-and-licenses)
- [Swift](../README.md#tool-downloads-and-licenses)
- [curl](../README.md#tool-downloads-and-licenses)
- [pyGenomeViz](../README.md#tool-downloads-and-licenses)
- [GTDB-Tk](../README.md#tool-downloads-and-licenses)
- [CORASON](../README.md#tool-downloads-and-licenses)
- [NPLinker](../README.md#tool-downloads-and-licenses)
- [PRISM](../README.md#tool-downloads-and-licenses)
- [GNPS / MASST](../README.md#tool-downloads-and-licenses)
- [SIRIUS / CANOPUS](../README.md#tool-downloads-and-licenses)
- [Pfam](../README.md#tool-downloads-and-licenses)
- [MIBiG](../README.md#tool-downloads-and-licenses)
- [UniProt / Swiss-Prot](../README.md#tool-downloads-and-licenses)
- [NCBI BLAST databases](../README.md#tool-downloads-and-licenses)
- [antiSMASH web server](../README.md#tool-downloads-and-licenses)
- [MIBiG downloads](../README.md#tool-downloads-and-licenses)
- [NCBI BLAST web service](../README.md#tool-downloads-and-licenses)
- [EMBL-EBI BLAST service](../README.md#tool-downloads-and-licenses)
- [NCBI E-utilities](../README.md#tool-downloads-and-licenses)
- [NCBI Datasets](../README.md#tool-downloads-and-licenses)
- [NP Atlas](../README.md#tool-downloads-and-licenses)
- [TYGS](../README.md#tool-downloads-and-licenses)
- [BacDive](../README.md#tool-downloads-and-licenses)
- [GTDB](../README.md#tool-downloads-and-licenses)

## Core concepts

### 1. BGC — biosynthetic gene cluster

An antiSMASH-called genome region containing genes associated with specialized
metabolism. One biological pathway can span several calls in a fragmented assembly.
The call describes encoded capacity; identifying a produced compound needs other evidence.

Find it in `*_2_inventory.csv`. Identify each locus as
**strain / full node-or-contig / region / BGC alias**, using one source record.
The `BGC###` alias alone is local to that run.

### 2. KCB — KnownClusterBlast

antiSMASH's comparison of a region against characterized clusters in MIBiG, the
reference collection of known clusters. Three numbers come out of it, and they are
not the same thing:

- **KCB similarity percent** (`KCB_similarity_pct`) is antiSMASH's own percent for the
  top hit. Mamey bands it: **high** at 70 or above, **moderate** at 40 or above, **low**
  above 0, **none** at exactly 0. Missing, nonnumeric or out-of-range (outside 0–100) values are **unresolved**, not zero.
- **KCB cumulative score** (`KCB_score`) is a summed BLAST score. It grows with the
  size of the match and is not a percent.
- **KCB protein hits** counts matched proteins.

`KCB_evidence_state` says where the match columns came from:

| Value | Meaning |
|---|---|
| `KNOWNCLUSTERBLAST_OBSERVED` | A KnownClusterBlast file had hits. |
| `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED` | The region's KnownClusterBlast file was read as a no-hit report and no hit rows were parsed. It is not checked against the JSON, so it is not a validated negative. A missing or unreadable file never gives this state. |
| `CLUSTERBLAST_FALLBACK_OBSERVED` | Accepted ClusterBlast or SubClusterBlast records supplied fallback evidence because no qualifying KnownClusterBlast record was assigned. A recognized KnownClusterBlast no-hit report blocks fallback. Check these hits by hand. |
| `UNKNOWN_KCB` | No KCB or fallback record was assigned to the region. The file may be missing, unreadable, unsupported or not matched to the region, so check the file and parse states. It does not mean low similarity, and it is not a negative. |

A leading `~` before a reference compound name means “resembles.” A high band is
similarity, not compound identity. “KCB-dark” must name the admitted source and state. An observed, scoped no-hit
report differs from missing, unreadable, unsupported or unbound evidence; neither
is proof of new chemistry or a complete negative search. Other diagnostic evidence
can still guide review. See [reading your results](../docs/READING_YOUR_RESULTS.md).

### 3. Corrected BGC count

A weighted summary of region boundary categories:
**Interior × 1.0 + Edge × 0.5 + Full-contig × 0.25**, rounded to two decimals by
`mamey/assembly.py::corrected_bgc_count`.

Report it with the raw region count and boundary distribution. A weight of 0.5
is a scoring rule, not a measurement that half a pathway was recovered.
Use matched processing and settings when comparing these counts.

### 4. Edge status

The called region's position relative to contig boundaries. Unknown contig
length gives **Unknown**. A span of at least 95% of the contig gives **Full-contig**
before topology is considered. Otherwise circular records give **Interior**;
a linear or unknown-topology record within 5,000 bp of either end gives **Edge**.

These labels describe geometry. Read the gene evidence separately when assessing
whether a pathway is complete. The terminus-truncation heuristic uses a 500-bp contig-end margin,
not necessarily an exact terminal boundary; its other pairing guards still apply.

<a id="5-architecture-confidence-ae-and-the-three-confidence-axes"></a>
### 5. Architecture confidence (A–E) and the confidence fields

The A–E grade summarizes structural evidence from boundaries, annotations,
length and selected supporting signals. It is separate from product-class
confidence and from lead confidence. The four fields are in the table under
**Architecture confidence codes**.

`Arch=A, Class_Conf=LOW` can describe a structurally clear region whose class is
uncertain. Keep the fields separate when reading a result. Older files can label
class confidence `Arch_Conf`; check their schema before comparing columns.

### 6. BGC-inventory assembly tier and fragmentation tier

`assembly_tier` summarizes the percentage of BGC calls away from contig edges.
`fragmentation_tier` describes sequence contiguity using contig count and N50.
A genome can score favorably on the first while remaining fragmented on the second.

Use the boundary summary for BGC recovery and contig/N50 measures for genome
contiguity. Genome-size and contamination warnings are separate checks.

### 7. RG-GMCI and the rescue layer

RG-GMCI proposes candidate relationships between fragments using reference
similarity and gene context. Keep the candidate pair, supporting sources and
recorded rule together. Its routing bonus changes review priority.

The contigs remain separate sequences. Compare competing partner assignments
and the actual supporting genes before interpreting a pair as one split locus.
See the detailed rescue definitions below for the selected workflow's fields.

### 8. CCTT / T43 class-trigger framework

CCTT (Compound-Class Trigger Table) signals flag genes or motifs associated with
biosynthetic classes. T43 is the trigger set. The class codes are HAL (halogenase),
LAN (lanthipeptide), TET (tetronate or spirotetronate), PHO (phosphonate), NUC
(nucleoside) and ENE (enediyne). They can draw attention to regions with weak or
unavailable KnownClusterBlast evidence. The trigger set is `CCTT_PATTERNS` in
`mamey/source_scans.py`. A corroborated class-defining trigger on a compatible locus can drive
the diagnostic bonus and Medium floor; tailoring-only or promiscuous triggers do not receive
that floor by themselves.

Report both the number of hits and the number of regions containing them.
Several marker hits in one region are different from a marker spread across
several regions.

### 9. Marker registry

The diagnostic-marker registry (`mamey/mamey_markers.py`) gives each scoring signal a stable ID,
evidence tier, class and claim ceiling. It spans domain-class, CCTT, regulator, TFBS, maturation,
resistance, transporter, chitin and fragment-rescue markers. Query the current registry for its
count; do not copy an older total. It connects a score to the annotation or motif that triggered it.

Look for marker IDs in the board and evidence-traceability records. The
real-anchor rule matches keywords to strings antiSMASH actually emits; use the
recorded match when explaining a score.

### 10. Mamey triage tier / routing prior

The triage tier tells you where the engine suggests spending review effort.
It uses the largest antibacterial, antifungal or novelty routing score, followed
by diagnostic floors and other scoring rules.

`mamey/scoring.py::triage_bgcs` uses **Exceptional ≥85**, **High ≥70** and
**Medium ≥50**. Below 50, class policy selects **Low** or **Inventory**.
Read these as prioritization categories rather than measured activity.
A downstream Wet-Lab score is a separate metric.

### 11. Diagnostic bonus & diagnostic floor

A diagnostic bonus changes a routing score. A diagnostic floor can raise an
eligible candidate to Medium when corroborated class evidence warrants attention
despite weak or unavailable KCB evidence.

Eligibility, tailoring-only exclusions and later standing-rule or RiPP downgrades
still apply. Read the score-rationale record, including
`AF_DIAGNOSTIC_TRIGGERS`, to see which rule affected that region.

### 12. Standing rules and workflow-scoped exclusions

A standing rule changes how a particular signal is used in a named workflow.
Read its current scope: a historical prevalence note or neutral annotation does
not automatically exclude a region from every comparison.

For cohort comparisons, keep the selected rule, measured cohort and denominator
with the result. Revisit an earlier interpretation when its evidence or scope changes.

### 13. Claim-safety vocabulary

Use language that matches the evidence: sequence predictions describe capacity,
reference comparisons describe similarity, and measured results name their assay
conditions. Missing or unrun evidence stays marked as missing.

The `[EG]` and `[VL]` tags and the claim ceiling are defined in the
[claim-safety table](#claim-safety-vocabulary). Keep strain-level
bioactivity with its material, assay and source; connecting it to an individual
locus requires separate evidence.

### 14. Mode B

A written interpretation of one locus, built from its full gene roster and
supporting sources. The default full48 profile uses **§1–§48**; the optional
current50 v2 profile uses 50 sections. Follow the
[authoring walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md) for the selected profile.

The template, authored card, verification report and saved package record are
different files. Keep `document_state`, typed evidence states and complete locus
identity with the card. Distinguish nr, NCBI ClusteredNR and local Swiss-Prot matches.

### 15. Evidence axes & legacy lead classes (A / B / C)

Evidence axes keep different reasons for pursuing a region visible. The axes are
listed in the table under [Evidence axes](#evidence-axes--legacy-lead-classes-a--b--c). Some
historical cohort workflows combine them into A/B/C lead classes. Those labels
are separate from the current Mamey triage tiers.

Use the emitting workflow's rules, weights and cohort denominator when comparing
classes. Recompute a cohort result after changing its membership.

### 16. Compound-class annotation

A label for the type of chemistry suggested by product annotations, class
diagnostics and reference matches. Read the class label together with its source
and supporting references.

Class matrices summarize a selected cohort. Recompute them after merging cohorts
so their counts and membership describe the new set.

## Enumerations & code tables

*The sections below are scan-friendly lookup tables. They hold codes, classes, and status values you match against output. The concepts behind them live in **Core concepts** above.*

## BGC classes (antiSMASH product annotations)

These are antiSMASH product-class annotations. Read the examples as reference-class
context; the core BGC definition explains what a call establishes.

| Term | Full name | What it means in plain English |
|---|---|---|
| T1PKS | Type I polyketide synthase | A large assembly-line enzyme that builds polyketide natural products (e.g. erythromycin, rapamycin). A class annotation does not establish the query isolate's activity. |
| T2PKS | Type II polyketide synthase | An iterative enzyme system making aromatic polyketides (e.g. tetracyclines, anthracyclines, angucyclines). A class annotation does not predict the observed spectrum or activity of this isolate. |
| T3PKS | Type III polyketide synthase | Simpler single-enzyme PKS; makes flavonoids and some phenolic compounds. |
| transAT-PKS | trans-acyltransferase PKS | A Type I PKS variant where the acyltransferase acts in *trans* (as a standalone enzyme). Inspect actual boundary and assembly evidence before proposing a split. |
| PKS-NRPS hybrid | Hybrid assembly line | An annotation combining polyketide and peptide machinery; inspect protein and module evidence rather than inferring one complete megasynthase. |
| hglE-KS | Heterocyst-glycolipid KS-like | A KS domain related to cyanobacterial glycolipid synthesis; used as a marker for certain reducing polyketide assemblies. (See *hglE-KS-PREV-001* under standing constraints.) |
| NRPS | Non-ribosomal peptide synthetase | Assembly-line enzyme building peptide natural products without the ribosome (e.g. vancomycin, daptomycin). |
| NRPS-like | NRPS-related | Has NRPS domains but doesn't follow the standard modular architecture; often makes small aryl-acid or diketo compounds. |
| RiPP | Ribosomally synthesized and post-translationally modified peptide | A peptide made by the ribosome, then chemically modified. Includes lanthipeptides, thiopeptides, sactipeptides. |
| Lanthipeptide (class I–IV) | Lanthipeptide | A RiPP with thioether (lanthionine) bridges. Class III made by LanKC multifunctional synthetase. Activity requires separate evidence for the selected product. |
| Thiopeptide | Thiazolyl peptide | A heavily modified RiPP with a central pyridine/dehydro-ring; includes characterized reference products such as thiostrepton; a query annotation is not an activity measurement. |
| LAP | Linear azol(in)e-containing peptide | A RiPP class with heterocyclized cysteine/serine residues; includes the microcin/plantazolicin family. |
| Lassopeptide | Lasso peptide | A RiPP threaded into a knot-like lasso fold; stability and activity require measurements for the selected product. |
| Sactipeptide | Sulfur-to-alpha-carbon peptide | A RiPP with sactionine (Cα–S) bridges installed by a radical-SAM enzyme. |
| RaS-RiPP / ranthipeptide | Radical-SAM RiPP | A RiPP modified by a radical-SAM maturase; the annotation alone establishes neither new chemistry nor a completed no-hit search. |
| NI-siderophore | NRPS-independent siderophore | An iron-scavenging molecule made without an NRPS assembly line. |
| NRP-metallophore | Non-ribosomal peptide metallophore | A metal-chelating NRP; metal binding and any additional activity require product evidence. |
| Betalactone | β-Lactone | A four-membered ring lactone; electrophilic warhead that inhibits serine hydrolases and proteases. A class annotation does not establish bioactivity. |
| Spirotetronate | Spirotetronate | A polyketide with a spiro-linked tetronic-acid ring; includes reference products such as abyssomicin and kijanimicin; the query locus still needs product evidence. |
| Enediyne | Enediyne (9-/10-membered) | A class annotation with characterized DNA-damaging reference products such as calicheamicin; it does not establish query-product identity or potency. Cytotoxicity caveats apply (handling per standard lab SOPs); see *T43-ENE / [E-signal]*. |
| Ansamycin / ansa-PKS | Ansamycin | A polyketide with a macrocyclic *ansa* bridge across an aromatic core (e.g. rifamycin). |
| Glycopeptide | Glycopeptide NRPS | A cross-linked, glycosylated heptapeptide class (e.g. vancomycin, kistamicin). Inspect any *VanHAX*-like annotation as separate source-derived evidence. |
| Aminoglycoside / amglyccycl | Aminoglycoside / aminocyclitol | Sugar-based antibacterials (e.g. streptomycin, kanamycin); may carry *APH/AAC* self-resistance. |
| Nucleoside | Nucleoside antibiotic | A modified-nucleoside scaffold; includes chitin-synthase-inhibiting antifungals (e.g. nikkomycin/polyoxin class). Keep the actual KCB source and state with any no-match claim. |
| Azoxy / guanidinotide | Azoxy / guanidino natural products | Specialized nitrogen-rich warhead classes flagged for novelty. |
| Terpene | Terpene/terpenoid | Built from isoprene units; includes antibiotics, pigments, and volatile compounds. |
| Saccharide | Sugar/glycoside | Carbohydrate-related class annotation. Inspect the actual backbone and tailoring evidence before assigning a glycosylated product. (See *saccharide-gating* under standing constraints.) |
| Butyrolactone | γ-Butyrolactone | Signaling-related annotation. Each workflow sets its own routing for it, so it is not excluded everywhere. The label does not show expression. |
| Ectoine | Ectoine | Compatible-solute class annotation. Its token participates in the bottom-tier housekeeping policy below the initial score threshold; diagnostics and later guards still apply. It is not an unconditional Inventory cap for every ectoine-labelled region. |
| Indole | Indole-derived | Clusters making indole-containing metabolites (some pigments, some bioactive). |
| Phosphonate | Phosphonate | C–P-bonded compounds (e.g. fosfomycin class); may carry fosfomycin self-resistance. |
| Redox-cofactor | Redox cofactor | Biosynthesis of cofactor-like small molecules; usually primary-metabolism-adjacent. |
| Melanin | Melanin | Pigment biosynthesis. |
| Fatty acid | Fatty acid | Lipid/fatty acid biosynthesis cluster. |
| NAPAA | Non-alpha poly-amino acids | Includes poly-gamma-glutamate-like annotations; product function and activity require separate evidence. Registry-neutral (listed, not interpreted; neither downgraded nor lead-blocking). |
| Halogenated | Halogenated compound | Halogenase-associated annotation: modification context, not identification of a chlorinated or brominated product. |

## Scan names and abbreviations

Mamey runs deterministic annotation and geometry scans over the supplied antiSMASH
records. Each record says which scans ran and on what input. A summary page does not mean
every scan ran on every region.

| Abbreviation | Full name | What it checks |
|---|---|---|
| KCB | KnownClusterBlast sweep | Reads the KnownClusterBlast results antiSMASH already wrote, region by region, with a typed state such as `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`. Mamey runs no new search. Keep the reported similarity percent separate from the cumulative score; neither establishes cluster identity. |
| RG-GMCI / RGGMCI | Reference-Guided Genome Mining Candidate Inference | Links fragmented BGC regions that map to the same reference producer cluster. Candidate inference only; it does not join contigs. See [RG-GMCI](#7-rg-gmci-and-the-rescue-layer). |
| FLBR | Fragment-Linkage BGC Recovery | Census of fragmented megasynthase (PKS/NRPS) sets across contigs — flags LMPKS_FRAGMENT_SET; identifies the candidate fragments that EFLS/RG-GMCI then link (a detection step that feeds recovery, not the linkage itself). The README labels the same scan the "fragmented-megasynthase census". |
| EFLS | Edge-Flank Linkage Scan | Preliminary shared-label pair heuristic over a capped BGC set. Skips pairs whose two records are both exactly Interior; scores shared product, MIBiG, cassette and CCTT labels. It does not compare raw contig ends, require different contigs or establish physical linkage. |
| CCTT | Compound-Class Trigger Table | Flags specific biosynthetic signals: HAL (halogenase), LAN (lanthipeptide), TET (tetronate/spirotetronate), PHO (phosphonate), NUC (nucleoside), and others. A CCTT trigger is the per-BGC signal the marker-aware scorer reads. |
| CGAD | Chitinase Genome Architecture Detection | Detects chitin-degrading enzyme families (GH18, GH19, AA10_LPMO, CBM_CHITIN, GlcNAc). Reports chitin/glycan annotation context within the supplied input scope. Do not infer that every scorer branch requires this scan or that a hit demonstrates chitin use or antifungal activity. |
| UMED | Unclustered Maturation Enzyme Detection | Scans maturation keyword patterns and couples hits to each BGC within a 5,000-bp flank. For selected family-enriched product tokens, any coupled hit yields IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED and no hit yields MATURATION_GAP_SOURCE_DERIVED; other products are NOT_MATURATION_GATED. This does not verify the full required enzyme complement, precursor presence, function or a separately rescued enzyme. Missing/unrun evidence is not absence. |
| FLBR/EFLS/RG-GMCI trio | Fragment review context | FLBR records a motif/count-based megasynthase census and fragment flags; EFLS nominates shared-label pairs; RG-GMCI retains its separate reference/geometry candidate-inference contract. Shared source annotations are not automatically independent corroboration. None physically rejoins contigs or establishes a single shared pathway. |
| bldA/TTA | bldA codon scan | Counts TTA codons in BGC-overlapping CDS: T1 records zero TTA counted, T2 one or two, T3 three to five, T4 six or more. A T1 with missing sequence or zero `total_codons` is missing evidence, not a measured absence. Recognized non-actinomycetes get NOT_APPLICABLE and keep their counts; unknown taxonomy needs review. A burden flag does not measure expression or prove bldA dependence under a selected culture condition. |
| TFBS | Transcription Factor Binding Site scan | Counts regulatory motifs (GBL/AdpA, DasR, BldD, PhoP, SARP) near BGCs; guides induction strategies. (See *Regulatory elements* below.) |
| CCSM | Cross-Cohort Strain Module | Cross-strain comparison module: compares a strain's BGC/marker profile against the rest of the cohort. |
| DAPR | Antibacterial/antifungal judgment framework | Keeps AB and AF prioritization separate. Its output depends on the builder that writes it: it is not a fixed top-three list, and it does not measure activity. |
| LMPKS | Linear Megasynthase PKS | Historical label within LMPKS_FRAGMENT_SET. The current FLBR flag uses KS-like pattern counts plus fragmented PKS/NRPS/transAT product labels; it does not establish linear assembly architecture, polyether chemistry or ionophore activity. |

**CCTT counts:** `cctt.counts` counts gene/motif matches across the genome;
`cctt.trigger_bgc_counts` counts the distinct regions containing them.
Eight hits in one region and eight hits across eight regions describe different distributions.

---

## Regulatory elements & TFBS

The TFBS scan records preliminary sequence-pattern matches in upstream windows.
Inspect missing contigs, clipped windows and the selected motif rules. A match
does not establish regulator binding, expression or successful induction.

| Regulator | What it is | Why it matters here |
|---|---|---|
| SARP | Streptomyces Antibiotic Regulatory Protein | A SARP-like regulator annotation is a candidate regulatory clue. It does not prove pathway regulation, an antibiotic product or expression. Read its source and locus context. |
| DasR | GlcNAc-responsive global repressor | Links nutrient sensing (N-acetylglucosamine, a chitin breakdown product) to antibiotic onset. A DasR site is a weak positive (a fractional point) in the score. |
| AdpA / GBL | A-factor / γ-butyrolactone cascade | The quorum-sensing developmental switch; GBL/AdpA control timing of secondary metabolism. |
| BldD | Master developmental repressor | Gatekeeps the switch from growth to sporulation/secondary metabolism. |
| PhoP | Phosphate-response regulator | Couples phosphate limitation to antibiotic production; relevant to media design. |

---

## Architecture confidence codes

Mamey assigns the A–E structural grade to every BGC from its position in the assembly.

| Code | Name | Meaning |
|---|---|---|
| A | Interior, coherent | Interior with a core-bearing product and length ≥10 kb, or a guarded compact chemical-hybrid promotion. Structural heuristic, not pathway-completeness proof. |
| B | Interior, limited/compact | Interior with core annotation, or with a KCB percent similarity of 70 or more, that does not meet the A branches; a strong KCB percent can support B without core annotation. |
| C | Edge, core-bearing | Edge with a recognized core-bearing product annotation. Partial interpretation only. |
| D | Edge limited / Full-contig core-bearing | Edge without core annotation, or Full-contig with core annotation. Keep geometry and partial-capacity caveats. |
| E | Other weak/ambiguous cases | Remaining cases, including Full-contig without core annotation or Unknown geometry. Inventory-level architecture interpretation. |

The four confidence fields in `*_4_triage_board.csv` answer different questions:

| Column / field | What it measures | Values |
|---|---|---|
| `Arch` (architecture_confidence) | Structural heuristic from the recorded geometry and annotations — the A–E grade above, not proof of a complete locus. | A–E |
| `Arch_Capacity` (architecture_capacity) | The claim-safe class-capacity call — a class *name*, not a confidence. | e.g. "lanthipeptide-class capacity" |
| `Class_Conf` (architecture_class_confidence) | Confidence in that class call. | HIGH / MODERATE / LOW |
| `claim_confidence` (B1) | Lead-claim label mapped from the A–E architecture grade by the current scorer; distinct from product-class confidence. It does not measure assay activity or product identity. | High / Moderate-High / Moderate / Low-Moderate / Low; Unknown fallback |

`Composite_region` fires when `Single_protocluster_count >= 3`.
`Overmerge_state` reports the E5 verdict: `OVERMERGE_SUSPECT`,
`COHERENT_CHEMICAL_HYBRID` or `NOT_VERIFIABLE`. Use `Protocluster_count`
for the number of resolved antiSMASH protoclusters, including a two-protocluster merge.

---

## Edge status (used in the corrected count)

The truncation label that drives the corrected count:

| Status | Meaning | Weight in corrected count |
|---|---|---|
| Interior | Does not trigger current boundary tests; circular records reach this branch only after the 95%-span test. It describes the region's position on its contig, not that every gene or locus was detected | 1.0 |
| Edge | Within 5,000 bp of either contig end on linear/unknown topology | 0.5 |
| Full-contig | Region span is at least 95% of contig length, tested before circular topology | 0.25 |
| Unknown | Contig length unavailable/nonpositive; preserve missingness rather than infer geometry | Preserve producer’s separate handling |

This label is Mamey's own measure, from `mamey/parsers.py::_edge_status`. antiSMASH writes a second, different flag: `/contig_edge` on each region feature of its GenBank files. The two do not always agree. In one isolate's antiSMASH result, for example:

- A region that ends 4,626 bp from its contig end is Edge here, and antiSMASH records `/contig_edge="False"`.
- A region about 5.8 kb and 19 kb from its contig ends is Interior here, and antiSMASH records `/contig_edge="True"`.

Which tools use which:

- The corrected count, the assembly tier and the inventory `Boundary` column use this label.
- The split detector (`mamey/split_detector.py`) and the RG-GMCI edge-pair scope (`mamey/rggmci.py`) read antiSMASH's `/contig_edge`. RG-GMCI uses this label for a region only when its GenBank flag is missing or its region features disagree.

Name which measure a table or sentence uses. A difference between the two is not an error in either.

---

## Evidence axes & legacy lead classes (A / B / C)

Evidence axes remain separate because they answer different questions. A
downstream builder may combine selected axes, but its versioned rule and
denominator must travel with the output.

| Axis | Question it answers |
|---|---|
| Structure / completeness | Is the visible locus coherent and physically complete enough for the proposed class? |
| Similarity | Does the locus resemble a characterized reference cluster? |
| Novelty / reference darkness | How weakly is the locus represented in the bound reference channels? |
| Diagnostic machinery | Do class-compatible genes, domains, or resistance signals corroborate the class? |
| Regulation / expression planning | Are pathway-linked regulatory signals present? This is not expression evidence. |
| Authored judgment | What claim-safe synthesis did the current Mode B review reach from the bound evidence? |

**Class-A / B / C** are legacy judgment-layer labels from selected cohort builders.
Read the emitting file's rule, version and denominator when comparing them.

---

## Marker-aware scoring & the diagnostic floor

| Term | Meaning |
|---|---|
| T43-NUC | A nucleoside diagnostic trigger. A corroborated, class-compatible T43-NUC trigger can add the AF diagnostic bonus and contribute to the Medium floor; other eligibility, mobile-element, standing-rule and short-fragment guards still apply. It is a routing signal, not an assay result or named product. |
| Diagnostic floor | An eligible corroborated class marker or cargo-aware T1 self-protection signal can raise Low/Inventory to Medium. Tailoring-only exclusions and eligibility checks apply; later standing-rule and short RiPP-fragment guards can lower the resulting tier.  |
| AF_DIAGNOSTIC_TRIGGERS | The antifungal-diagnostic markers that can fire the floor: T43-NUC, T43-PTM and T43-PYE (`mamey/scoring.py`). |
| AB_DIAGNOSTIC_TRIGGERS | The antibacterial-diagnostic markers: T43-LAN, T43-LASSO, T43-THA, T43-PHO, T43-AMC, T43-BLA, T43-GPA and T43-BLT (`mamey/scoring.py`). Read the installed set; an older list may be incomplete. |
| NOVELTY_KEYWORDS | Routing weights per product token in `mamey/scoring.py`, for example `ranthipeptide` 12. There is no `sactipeptide` entry, so do not carry one class's weight to another. They are routing constants, not activity or novelty measurements. |
| Real-anchor rule | Audit every keyword against the strings antiSMASH *actually emits* (e.g. "nucleoside", "SGR PTMs"), not textbook compound names (e.g. "nikkomycin"). |

---

## Mamey triage tiers

Mamey assigns every BGC a routing tier from its AB, AF, and novelty priors,
then applies corroborated floors and fail-safe downgrades.

| Tier | Criteria | Treatment |
|---|---|---|
| Exceptional | Current best routing prior ≥85 | Highest engine routing prior; still capacity-level and subject to guards |
| High | Current best routing prior ≥70 | High routing priority |
| Medium | Current best routing prior ≥50, or an applicable diagnostic/machinery floor | Review priority; a floor does not raise claim confidence |
| Low | Below 50 with a resolved specialized class outside the governed Inventory policy | Keep visible at lower routing priority |
| Inventory | Below 50 and unresolved or covered by the governed Inventory policy | Keep in the complete inventory; do not equate with biological unimportance |

The thresholds above describe the current engine and must be checked against
`mamey/scoring.py::triage_bgcs` when used outside this bundle.

---

## Resistance gene families

| Term | What it is | Self-protection significance |
|---|---|---|
| Beta_lactamase_fold | β-Lactamase-fold annotation | Generic resistance-like group in the current scan (T2 when no diagnostic group outranks it), not standalone T1 self-protection or antibacterial-production evidence. |
| APH/AAC | Aminoglycoside phosphotransferase / acetyltransferase-like annotation | `APH_AAC` is in the diagnostic-group set, subject to the local sugar-kinase/glycogen-trehalose veto. An annotation does not show self-resistance. |
| Erm_methylase | Erythromycin ribosome methylase | T1 diagnostic: typically paired with macrolide biosynthesis |
| VanHAX_like | Vancomycin resistance cluster | T1 diagnostic: paired with glycopeptide biosynthesis |
| Fosfomycin | Fosfomycin resistance | T1 diagnostic |
| Self_resistance_general | General self-resistance annotation | T2: supportive but non-specific |

**Resistance tiers:**

- **T1** (`T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED`) — a diagnostic-group annotation coupled to the region; inspect class concordance and source limits
- **T2** (`T2_RESISTANCE_LIKE_SOURCE_DERIVED`) — generic resistance-like annotation without an admitted diagnostic group
- **T3** (`T3_TRANSPORTER_ONLY_ROUTING`) — coupled transporter annotation when no resistance group qualifies; routing, not demonstrated efflux
- **NULL** (`NULL_NO_SOURCE_DERIVED_RESISTANCE`) — no qualifying source-derived resistance or transporter signal in the examined scope

**Proximity rule:** a resistance marker only counts toward a lead if it sits *near* the BGC. A genome-wide β-lactamase elsewhere on the chromosome is not self-protection evidence for a distant cluster.

---

## BGC-inventory and fragmentation tiers

`assembly_tier` is derived only from the proportion of BGC calls that are Interior:

| `assembly_tier` | Interior-BGC percentage | Meaning |
|---|---|---|
| GOOD | ≥70% | Most called regions avoid contig boundaries |
| MODERATE | ≥45% | Mixed boundary recovery |
| POOR | ≥20% | Many called regions meet contig boundaries |
| VERY_POOR | <20% | Most called regions meet contig boundaries |
| UNKNOWN | unavailable denominator | Boundary-recovery tier cannot be computed |

`fragmentation_tier` is a separate ordered contig/N50 classification. The first
band satisfying both limits wins:

| `fragmentation_tier` | Current ordered band |
|---|---|
| CLOSED | ≤2 contigs and N50 ≥1,000,000 bp |
| CONTIGUOUS | ≤20 contigs and N50 ≥500,000 bp |
| DRAFT | ≤100 contigs and N50 ≥100,000 bp |
| FRAGMENTED | ≤1,000 contigs and N50 ≥10,000 bp |
| HIGHLY_FRAGMENTED | valid contig count but no earlier band matches |
| UNKNOWN | contig count unavailable or invalid |

Report raw region counts, weighted counts and these tiers together.
The core corrected-count definition explains the weighting and its limits.

## Evidence-ledger and identity states

| State | Where | Meaning |
|---|---|---|
| `MODULE_ABSENT` | tab-reconcile ledger | The antiSMASH module's output is missing from the record. Nothing was searched; this is not a negative result. |
| `NOT_RUN_LOW_GC` | tab-reconcile ledger, TTA row | antiSMASH skipped the TTA codon scan because genome GC is below its threshold. An empty list here is not "no TTA codons". |
| `NO_RESULTS_FOR_REGION` | tab-reconcile ledger, ClusterBlast rows | The ClusterBlast JSON has no entry for the requested region. Another region's entry is never used in its place. |
| `IDENTITY_HOLD` | tab-reconcile | The requested region is not on the chosen record. The command stops instead of reporting another region's evidence. |
| `AMBIGUOUS_TRIAGE_BOARDS` | seal-package, claim-safety names | The package holds more than one `*_4_triage_board.csv`. Keep exactly one board per package. |
| `RUN_AMBIGUOUS` / `RUN_NOT_IN_DB` / `RUN_UNFINISHED` | BiG-SCAPE widgets and figures | The database holds more than one finished run, the named run has no families, or the run has no `end_time`. Pass `--run-id` with a finished run. |

---

## Key metrics

| Term | Meaning |
|---|---|
| KCB similarity band | The band defined under [KCB](#2-kcb--knownclusterblast), from the antiSMASH percent. The percent is the rank-1 KnownClusterBlast `similarity` from the result JSON, kept only when its accession matches the rank-1 MIBiG accession in the text file; `kcb_similarity_state` says why it is missing. The same cut-offs drive the strong-match novelty penalty, architecture grade B and the Mode B claim ceilings. |
| MIBiG | Minimum Information about a Biosynthetic Gene cluster database; reference collection of known BGCs |
| Interior % | Fraction of called regions assigned Interior under the selected producer's boundary rule; not evidence that every gene or the complete locus was recovered. |
| N50 | Contig length at which 50% of the assembly is in contigs this size or larger; proxy for assembly contiguity |
| Hallucination trap | A claim-calibration review or recorded trap entry. An empty or missing judgment field does not mean every BGC was checked or that no conflict exists. |
| Wet-Lab / WL score | A downstream experimental-priority metric emitted by selected judgment tools. It is separate from the Mamey triage tier and must identify its own versioned inputs and rule. |

---

## Claim-safety vocabulary

Use these terms when explaining the evidence behind a result.

| Term | Meaning |
|---|---|
| Biosynthetic capacity | The permitted way to describe what a cluster *could* make. "Biosynthetic capacity consistent with a glycopeptide" — never "produces vancomycin." |
| Claim ceiling | The maximum confidence a statement may reach for a given evidence level. Assembly fragmentation, locus boundary and product-claim evidence are separate axes. The fragment guard checks only selected named-reference or large-backbone cases and returns CLEAR, TRIPPED or UNKNOWN. The top-lead helper applies its own rules, which read the standing-rule flag, architecture, KCB percent similarity, protein-hit counts and class agreement. A fragment or an edge cluster lowers a ceiling only where one of these rules says so. |
| `[EG]` / `[VL]` | Evidence-tag on a verdict. `[EG]` = *evidence-grounded* but not literature-verified (provisional); `[VL]` = *verified against literature*. A project identifier or privacy tier never upgrades the tag. |
| Architecture Confidence | The A–E grade (above), reported alongside every claim so a reader sees the structural basis. |
| Evidence Traceability | A block linking each claim back to the specific scan/hit that supports it. |
| ~ (tilde) | "Resembles, is not." Prefixes any known-compound name attached by KCB (e.g. "~kijanimicin"). Similarity, not identity. |
| Bioactivity metadata | Optional typed isolate-level assay context. Omission is `NOT_SUPPLIED`; distinguish `NOT_OBSERVED`, `UNKNOWN`, `NEGATIVE` and `POSITIVE` as defined below. A measured negative is assay-scoped; no observation is attributed to a BGC without governed linkage. |
| Missingness vs absence | "Not found in this assembly" (a fragmented genome may simply not contain the region) is reported as *missingness*, never as proof a gene is *absent*. |

---

## Typed assay observations

Observation states apply to the recorded assay, target, tested material, dose,
time point and decision criterion. These isolate-level records need a separate
evidence link before activity can be assigned to a BGC. This schema admits only
`compound_linkage=NOT_ESTABLISHED`; an established locus/product link requires a
separately governed evidence workflow.

| Observation state | Meaning |
|---|---|
| `NOT_OBSERVED` | No assay observation is supplied; this is not a measured negative. |
| `UNKNOWN` | Context is supplied but an interpretable measured outcome is not established. |
| `NEGATIVE` | A bound measured result is negative under the stated assay conditions and criterion; it does not establish biological inactivity under every condition. |
| `POSITIVE` | A bound measured result is positive under the stated assay conditions and criterion; it does not establish a named compound, expression or locus-level causality. |

`bioactivity_metadata_v1` also records `metadata_state`: `NOT_SUPPLIED`,
`SUPPLIED_UNKNOWN`, `MEASURED_NEGATIVE`, `MEASURED_POSITIVE`,
`BIOACTIVITY_LEGACY_SHAPE_HOLD` or `LEGACY_UNTYPED_CONTEXT`.
Keep this field with the assay records, usage scope, receipt binding and
`compound_linkage`. Example or legacy metadata cannot supply a missing observation.

## Evidence, identity, portability, and authority vocabulary

These terms describe how the portable application finds and binds external
evidence, how Mode B reports readiness, and how release tooling separates a
candidate from an authorized release.

| Term | Meaning |
|---|---|
| Exact-locus identity | The mandatory display and join identity for one BGC: `strain / full node-or-contig / region / BGC alias`. The alias is last and source-scoped. Copy all four components from the same source row and check for missing or placeholder values before using an output. A validation pass alone does not establish that an identity is complete. |
| Source object | An external evidence file or dataset represented by its source role, logical locator, SHA-256, byte count, and binding/admission state. A path, filename, timestamp, or duplicate copy is not source authority by itself. |
| Logical locator | A portable reference such as `evidence://root-id/path` that resolves through runtime configuration. The portable-evidence contract separates machine-specific runtime paths from portable locators. It does not guarantee that every package or report hides local paths, so check a file before you share it. |
| Discovery catalog | A bounded inventory of candidate collections. `DISCOVERED_NOT_ADMITTED` means exactly that: discovery proposes material for review and does not authorize consumption. |
| Admission / collection decision | The recorded choice `CONSUME`, `REJECT_WITH_REASON` or `SUPERSEDED_WITH_RECEIPT` for a collection identified by its hash. `CONSUME` permits the workflow to read those files. |
| Exact-locus evidence states | `EXACT_LOCUS` is bound to strain, full node/contig, and region; `ALIAS_BOUND` lacks an independent full locator; `STRAIN_ONLY` is context only; `UNBOUND` cannot yet join; `ABSENT` means no matching artifact in the configured scope. `UNBOUND` and `ABSENT` are workflow states, not biological negatives. |
| Evidence-readiness states | `READY_BOUND` may be integrated; `AVAILABLE_UNINGESTED` must be ingested first; `NEAR_READY_ACTIVE_RUN` remains blocked while a run completes; `PRACTICALLY_ATTAINABLE` should be obtained before content QA; `STRUCTURALLY_UNAVAILABLE` and `NOT_APPLICABLE` require a typed reason. |
| Gene-first / sequence-first review | Build the canonical gene roster before prose and preserve its order. Bind a protein result by the exact locus plus protein SHA-256; a locus tag or similar name alone does not prove sequence identity. Every canonical gene remains in the denominator, including boundary/context genes. |
| Channel-separated BLASTp | NCBI nr, NCBI ClusteredNR, and local Swiss-Prot are separate evidence channels with separate named-match, alignment-metric, state, and coverage fields. Missing or unbound evidence in one channel is never filled from another. ClusteredNR is not nr; percent positives is not percent identity; similarity is not functional proof. |
| `document_state` / `evidence_state` | Two orthogonal Mode B axes. `document_state` says where the card is in the authoring/review ladder; `evidence_state` records bound, unbound, quarantined, unavailable, or not-applicable evidence. Read both fields to distinguish writing progress from evidence availability. |
| Privacy profile | User-owned policy mapping exact strain IDs to named access tiers. Unassigned strains inherit a required non-public default. Only a tier explicitly marked `public_export: true` maps to package `PUBLIC`; all others map to `PRIVATE`. |
| Package `PUBLIC` / `PRIVATE` | Binary run/export metadata used by package consumers. An exact privacy profile uses its required non-public default for unassigned strains. Without a profile or explicit public authority, the current resolver defaults to PRIVATE for every ID prefix; an admitted public override or exact public assignment has a separate recorded basis.  |
| Release/archive transaction states | **Source tree**, **staged tier tree**, **archive candidate**, and **verified archive** are distinct objects.  `PUBLIC_RELEASE` is a separately authorized promotion state; a CODE or `NOT_FOR_PUBLIC_RELEASE` candidate is not one. |
| Portable / offline core | The application, small reference assets, vendored fallbacks, and local wheel paths are designed to run without network access. Optional commands whose names or help explicitly say online may contact their named service and must keep provenance; their absence is an evidence gap, not a failed core extraction. |
| Sealed package | A package that passed the extraction and package-integrity checks for its recorded engine and inputs. `MAMEY_COMPLETE` reports that extraction state; written interpretation has a separate status. |
| Post-seal tool | A tool that uses an existing sealed package, such as Mode B, comparison or figure tooling.  Authoring can write package files and refresh checksums; validation normally writes a status receipt. |
| Mechanical gate / authority ceiling | A check of named conditions such as schema, hashes, identity or completeness. Read the check's scope and result; release decisions follow the separate release procedure. |

---

## Evidence sources and where to find the rules

The portable-evidence terms above are specified in
[PORTABLE_EVIDENCE_WORKSPACE.md](../docs/PORTABLE_EVIDENCE_WORKSPACE.md),
[MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md](../docs/MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md),
[MODE_B_SUPPORT_CARD_CONTRACT.md](../docs/MODE_B_SUPPORT_CARD_CONTRACT.md) and
[PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md](../docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md).

---

## Standing biological constraints

Permanent rules, learned across many strains, that override case-by-case interpretation. They exist to stop recurring over-claims.

| Constraint | Rule |
|---|---|
| NAPAA (poly-amino-acid class) | Current registry status is neutral, action none, lead_blocking false: no intrinsic comparison/ecological exclusion or score downgrade. Keep product tokens and interpret only bound evidence at its actual scope. |
| hglE-KS-PREV-001 | Current registry status is noted, scope informational, lead_blocking false. Historical prevalence is context, not by itself a comparative-ranking downgrade or a universal habitat claim. Separately, the current scorer’s direct hglE-product check can set a standing-rule flag when no CCTT trigger is present and lower the tier; inspect the actual flag and producer. The separate gene-level enediyne-artifact guard remains applicable; a zero/unbound KCB result does not prove new chemistry. |
| Saccharide-gating null | Workflow-specific product-token filter. The amino-acid summary excludes an exactly saccharide product set; genome-class displays park saccharide; genus/family comparisons have separately selected policies, including fatty acid. Keep source rows and the actual denominator. A class label does not prove absence of specialist chemistry. |
| Multi-siderophore flag | Carrying several siderophore systems recurs across many strains; treated as an iron-economy observation, not a per-strain distinction. |
| T43-ENE / [E-signal] | A genuine enediyne (`ene_KS`) carries an [E-signal] claim-safety note — cytotoxic/DNA-damaging class; cytotoxicity/self-protection review, handling per standard lab SOPs (no selective BSL-2 gate — selective biosafety flags give false reassurance). Confirm a genuine `ene_KS` call vs an `hglE-KS` cross-reaction at the gene level first. |

---

## Validation vocabulary

Terms used in the external-validation record (runs on public reference genomes that test whether the pipeline behaves).

| Term | Meaning |
|---|---|
| Type strain | Nomenclatural reference strain for a species. A public assembly is not itself proof of type status. In this workflow, label an assembly `[Type]` only with the required assembly-from-type-material provenance ([figure house rules](../docs/FIGURE_HOUSE_RULES.md), rule 7); a type-like strain name is insufficient. |
| Positive control | A bound reference input with a prespecified expected positive result for the named check. State the expected feature, method and failure criteria; recovery is not guaranteed by the label. |
| Negative control | A bound input with a prespecified expected negative result for the named check. It is not a claim that an entire organism lacks biosynthetic capacity. |
| Blinded prospective validation | Running the pipeline on a genome before checking the literature answer, so the call can't be tuned to fit. |
| Corrected-vs-raw percentile | A comparison of BGC-count ranks under the raw and boundary-weighted count rules in the selected cohort. Rank movement reflects those rules and denominator, not an independently validated measure of assembly quality or pathway recovery. |

---

## Ecological habitats & host systems

These are examples of recorded isolation-source or host-group labels, not a
required cohort composition. Report samples as deposited or isolated from their
recorded sources; a host association or symbiosis needs independent evidence.

| Term | Meaning |
|---|---|
| Attine / fungus-garden | Fungus-growing-ant or garden source label. Preserve the deposited host and material; the label alone does not establish a defensive symbiosis. |
| Bryophyte / lichen | Moss, liverwort or lichen source label. Preserve unresolved host identity rather than treating the group as a taxonomic determination. |
| Hymenoptera / bee | Bee/wasp host-group label. Preserve the actual deposited host and material; isolation from an insect does not by itself establish a symbiont. |
| Fungus-growing termite | An independent insect-fungiculture system (e.g. *Macrotermes*); a natural cross-system comparator to the attine ants. |
| Actinomycete | The bacterial group (Actinomycetota) that dominates this project; prolific producers of natural products. Genera here include *Streptomyces*, *Amycolatopsis*, *Pseudonocardia*, *Saccharothrix*, *Micromonospora*, *Nocardia*, *Actinomadura*, *Sciscionella*. |

---

## Release gates

Tier construction, package privacy and promotion to a public release are separate
controls. A release cut currently builds the CODE tier only; the cut process is in
[CUT_PROTOCOL.md](../CUT_PROTOCOL.md). The tier names come from `tools/tier_vocabulary.py`.

| Tier | Contents |
|---|---|
| `code` (CODE) | The runnable pipeline: engine code, tools, docs, examples and the wheelhouse. Private cohort data and internal working notes removed. |
| `clean` (CODE-analysis-free) | The code tier with worked strain-by-strain outputs also removed. |
| `cohort` (COHORT-public) | The code tier plus the public reference cohort data banks. Older archives call this tier `sid` (`SID-public`). |
| `merged` (MERGED-PRIVATE-scaffold) | Everything, including any `private/` tree and real strain identifiers. The operator's own copy; never published. |
| `public` (PUBLIC-RELEASE) | Same content as the code tier. An explicit promotion, separately authorized. |

Only `code` is cut by default. The other tiers refuse to build unless
`SAPOTE_ENABLE_DISABLED_TIERS=1` is set.

| Gate | Meaning |
|---|---|
| Technical release gates | Schema, tests, identity, checksum, membership, derivation and content-audit checks. Passing them creates technical evidence only. |
| Governance gate | A separately active, signed, non-invalidated decision required for `PUBLIC_RELEASE`. Candidate tiers remain candidates without it. |
| Leak/content audit | The staged public tree is checked for disallowed cohort identifiers, private paths and content, and other configured leaks. The archive still needs its own integrity check. |

---

## Plain-language terms (overloaded everyday words)

These familiar words have specific meanings in the bundle.

### Names

| Name | What it means here |
|---|---|
| Mamey | The deterministic engine: the Python layer that parses antiSMASH output and extracts the BGC inventory. It computes source-derived records and routing heuristics; authored biological judgment remains separate. |
| Sapote | The judgment layer: interprets Mamey's output and writes the claim-safe reports. Mamey + Sapote together = the bundle. |

### Overloaded common words

| Word | What it means in Sapote–Mamey |
|---|---|
| Gate | A bounded validation checkpoint. Its name and receipt say what it checked. |
| Cassette | A reusable biosynthetic logic pattern in the registry, used for marker-aware scoring. |
| Marker | A registered annotation or sequence-pattern signal with a named source, evidence tier and claim ceiling; inspect its specificity rather than treating a hit as functional proof. |
| Arm | A glycosylation arm: sugar-tailoring genes sitting outside the core BGC boundary. Reported as evidence, not proof of physical linkage. |
| Scan | One detection-module pass (CCTT, CGAD, EFLS, etc.). Each BGC carries "scan states." |
| Sweep | A pass over saved results for every region. The KCB sweep reads the KnownClusterBlast results antiSMASH wrote; it does not search MIBiG again. |
| Triage | Ranking BGCs by promise. The "triage board" is the ranked output. |
| Board | A results table in the package: the triage board (`*_4_triage_board.csv`) and the AB and AF lead boards (`*_4c_AB_lead_board.csv`, `*_4c_AF_lead_board.csv`). |
| Lead | A prioritized BGC candidate worth pursuing. Raising lead priority never raises claim confidence. |
| Manifest | Two senses: the `manifest.json` handoff object Mamey emits, and the release manifest listing shipped files. |
| Ledger | A named evidence or findings record. Check its producer: an append-only journal and a register that replaces entries have different persistence behavior. |
| Flank | A region next to a feature or boundary. The relevant scan defines its coordinate distance; EFLS currently compares shared labels and does not match raw contig-end sequence or prove the other half of a pathway. |
| Warhead | The reactive chemical group that gives a compound its bioactivity (e.g. a β-lactone electrophile). |
| Handoff | The structured transfer of data from Mamey to Sapote (and between the execution and judgment layers). |
| Card | A structured per-item write-up: a Mode B card per BGC, or an A5 fermentation card. |
| Tier | A named band whose meaning depends on the field: evidence tier, Mamey routing tier, privacy tier, or release tier. Never compare two "tiers" until their namespace is clear. |
| Register | A structured ledger such as a missingness, judgment, or output register. A missingness row records a workflow observation, not proof of biological absence. |
| Contract | The current named specification for the selected output/profile and its evidence requirements. It defines coverage and checks within the selected task. |
| Anchor | A publicly reproducible reference point (KCB anchor, calibration anchor) that grounds a threshold. |
| Band | A prevalence bracket (e.g. core / common / rare) used to judge whether a class is informative for comparison. |
| Split | A split pathway: one biosynthetic pathway whose genes are spread across two or more contigs (Split-A / Split-B). |
| Routed out | A class deliberately excluded from a track (e.g. cytotoxic-adjacent classes routed out of the antibacterial lead track). |
| Verdict | A Mode B verdict: the confirm/drop call on whether a candidate is genuine. |
| Profile | A scan profile: the assembled per-BGC summary of all scan results. |
| Class | Either a biosynthetic/compound class or a legacy A/B/C lead overlay, depending on context. Neither is the Mamey routing tier, and neither raises the claim ceiling. |

---


## Versioned implementation notes

Use these notes to read older outputs. Check the named current code, registry
or schema before using a formula or threshold from another build.

| Term | Full name | What it means in plain English |
|---|---|---|
| Standing-rule downgrade | Workflow-scoped routing/display consequence | Apply only a current rule's explicit action and scope. NAPAA is neutral; the hglE-KS/PREV-001 registry record is informational, while the scorer separately applies its conditional hglE-product/no-CCTT standing-rule guard. Genome-class displays park saccharide only, while genus/BiG-SCAPE family comparisons keep their separately selected wider policy. Preserve full product tokens, counts and provenance for audit. |
| RiQ | Reference-information quotient | A selected JSON-derived reference signal whose source/channel and region binding must remain explicit. In the current scorer, an admitted nonmissing value below 0.5 adds 10 to the novelty routing prior before other handling; it is not measured chemical novelty. The bounded walker keeps RiQ separate from its auxiliary leaf budget, but RiQ still has group caps, authority limits, source-conflict and unmapped/held states. “Exempt from the record cap” does not mean unlimited or complete. |
| Judgment store / register | Mode B persistence layer | The per-package store (`<strain>_judgment_register.json` + `judgment/*_mode_b.md`) that holds Sapote's Mode B cards durably.  |
| Mode B receipt | `mode_b_receipt.json` | The JSON a Sapote session emits at the end of a Mode B batch (`{strain_id, session_id, cards:[{bgc_id, mode_b_md, …}]}`). `python mamey_run.py ingest-receipts` consumes it to persist the cards into the judgment store and reconcile the workbook's E1 sheet. Fail-closed (unknown BGC skipped, never invented) and idempotent. |
| `doctor` / `inspect` / `explain` / `list-bgcs` | Environment, intake and package inspection | `doctor` checks the environment. `inspect <antiSMASH.zip>` previews raw antiSMASH ZIP intake before a run. `explain <package_dir>` summarizes an existing result package. `list-bgcs <package_dir>` prints its BGC inventory (optionally `--json`). These operations do not rerun extraction. From the bound bundle root, use `python mamey_run.py` before the command. |

### Selected persistence and report terms

| Term | Meaning and boundary |
|---|---|
| Compiled reader report | A reader view can be built from a partial package. Strict mode blocks open slots. Claim-safety findings block by default, unless an explicit draft override is allowed; strict mode ignores that override. A compiled report does not mean all judgment is complete. See [Mode B](../docs/MODE_B_USER_WALKTHROUGH.md). |
| Judgment-store section update | The current section updater replaces and deduplicates matching note sections. Card, note and register writes remain separate outputs; inspect failures and actual persisted state. |
| Historical glossary | The [retained correction layer](../docs/history/retired_458/user_guides/comprehensive_glossary.md) and snapshot preserve earlier formulas and their review history. This glossary does not vouch for the historical examples or replace the specialist guides. Check the current source before you reuse a historical recipe. |

### RG-GMCI rescue layer

*These fields appear on the ranked-pairs output and in Mode B cards. All remain candidate inference; none joins contigs at the nucleotide level.*

| Term | Full name | What it means in plain English |
|---|---|---|
| db_kind / CB–KCB separation | ClusterBlast database-of-origin tag | Each shared-reference hit is tagged by the antiSMASH file it came from. **knownclusterblast** is a characterized MIBiG cluster; similarity to it suggests a product class and does not identify the product. **clusterblast** is a cross-genome GenBank neighbor; it shows another genome carries similar genes for both fragments. **subclusterblast** is sub-operon hits and is excluded from rescue geometry. |
| rescue_evidence_base | Observed reference channels supporting a pair | `BOTH_KCB_AND_CB`, `CLUSTERBLAST_ONLY`, `KNOWNCLUSTERBLAST_ONLY` or `NONE`. An ONLY label does not mean the other channel was searched and came back negative. Shared upstream annotations are not independent corroboration. |
| functional_rescue_class | Relative recognized-role category | Uses core / (core + tailoring + transport + regulatory), excluding unrecognized roles; a zero denominator returns 0. Classes are `COMPLEMENTARY`, `BOTH_CORE`, `ACCESSORY_ONLY`, `AMBIGUOUS` or `UNKNOWN_NO_PROFILE`. Zero recognized roles does not show accessory genes; `BOTH_CORE` does not establish complete cores, paralogy or linkage. |
| subject-tiling verdict | Shared-reference gene-hit overlap category | `COMPLEMENTARY_SPLIT`, `OVERLAPPING_PARALOG`, `MIXED_SUBJECT_SIGNAL` and `INSUFFICIENT_SUBJECT_DATA` classify the selected subject-hit evidence; a terminus override can add `TERMINUS_TRUNCATION_SPLIT`. Disjoint or shared hits can motivate competing fragmentation/paralogy hypotheses but do not identify a unique partner, complete pathway or physical join. |
| Terminus-truncation rescue / TERMINUS_TRUNCATION_SPLIT | Coordinate-based candidate flag | Uses an Edge region within a 500-bp end margin, different-contig and class/small-partner predicates (Full-contig partner ≤25 kb). Low-complexity sequence can veto the override; unavailable sequence stays unresolved. A class-only flag does not promote a weak verdict. The flag does not establish a unique partner or physical join. |


### RG-GMCI read depth and residue tiling

*Both are report-only: they add fields to the ranked pairs and change no score or confidence*.

| Term | Full name | What it means in plain English |
|---|---|---|
| depth_flag | Contig-name depth comparison | Parses `_cov_<x>` values and rounds lower/higher to three decimals before comparing with 0.67: `DEPTH_CONSISTENT` at or above, `DEPTH_MISMATCH` below. `DEPTH_UNAVAILABLE` covers missing/unusable values or a nonpositive higher depth. This report-only name-derived comparison does not establish physical linkage, copy number or contamination. |
| residue tiling verdict | Coverage of shared reference proteins | Optional DIAMOND layer, requested by `--rggmci-diamond-db` or `diamond_db`. `COMPLEMENTARY_RESIDUES`, `OVERLAPPING_RESIDUES`, `MIXED_RESIDUES` and `THIN_RESIDUES` describe selected residue coverage, not proven fragmentation or paralogy. `NO_SHARED_MIBIG_REFERENCE` is scoped to the tested resource and matched references. `REGION_SOURCE_UNAVAILABLE` records missing region source. `NOT_TESTED` also covers pairs outside the selected scope; if the layer was not invoked, fields may be absent. Default scope is `st_paralog`; retain database, source and status. Report-only. |

---

## Mode B section terms

| Term | Full name | What it means in plain English |
|---|---|---|
| Ranthipeptide | Radical SAM RiPP subclass | A ribosomally synthesized and post-translationally modified peptide (RiPP) associated with radical-SAM maturation, a recognition element, and a precursor peptide. Additional tailoring can diversify the predicted scaffold. A specific locus still requires the complete exact-locus identity and gene-level evidence; class membership alone is not product identity. |
| Mode B quality floors | Card checks in `mamey/mode_b_quality_gate.py` | Usual HIGH/MID/LOW floors are 12,000/11,000/10,000 characters. Edge or Full-contig with known CDS count ≤22 uses 2,500; missing boundary or CDS does not qualify. Below 2,000 is STUB. Enrichment requires 2,000 characters from the first §11–§20 marker to the end; other content checks also apply. These are heuristics, not proof of sound reasoning. Do not pad a card to clear them. |
| §28 — Evidence provenance ledger | Mode B card section 28 within the current §1–§48 profile | A per-claim table recording the factual claim, evidence tier, source file or field, engine version, confidence, and update trigger. It supports surgical revision but does not itself validate the claim. |
| §30 — Experimental decision tree | Mode B card section 30 within the current §1–§48 profile | A structured set of unresolved questions, resolution experiments, expected card changes, and downstream consequences. It turns a card into a research plan without implying that any experiment has been performed. |

## Setup, clustering and phylogeny terms

| Term | Meaning and boundary |
|---|---|
| Pfam | A reference collection of protein-family profile HMMs used in domain annotation. Full Pfam and a scanner-specific HMM panel have different roles; provide the panel required by the consuming tool. See [external assets](../docs/EXTERNAL_ASSETS_GUIDE.md). |
| HMM / pressed HMM | A hidden Markov model represents a sequence-family profile. A pressed HMM database has HMMER companion index files (`.h3f`, `.h3i`, `.h3m`, `.h3p`) used by the relevant scanner; the source model file alone may not satisfy its prerequisites. See [BiG-SCAPE preparation](../docs/BIGSCAPE_GCF_WORKFLOW.md). |
| GCF | Gene cluster family: a grouping of BGCs under the selected similarity/clustering settings. Family membership or singleton status does not prove a common compound, activity or novel chemistry; fragmentation and input scope affect the comparison. See [BiG-SCAPE workflow](../docs/BIGSCAPE_GCF_WORKFLOW.md). |
| MLSA | Multilocus sequence analysis: phylogenetic comparison using an explicitly selected panel of sequence loci. The bundled five-protein-coding-locus driver is separate from its 16S extraction route; record loci, alignment and tree method rather than assuming every MLSA panel is identical. See [phylogenomics](../docs/phylogenomics.md). |
| 16S | The small-subunit ribosomal RNA marker used by the 16S routing/placement workflows. A 16S similarity or placement is sequence context, not an ANI measurement, compound call or automatic species assignment. See [phylogenetic autopilot](../docs/PHYLO_AUTOPILOT_WORKFLOW.md). |
| LWR | Likelihood-weight ratio in a phylogenetic placement result: relative support for candidate attachment edges under the selected reference alignment/tree and model. It is not a probability that an isolate belongs to a species. See [placement workflow](Phylogenetic-Placement.md). |
| Pendant length | The branch length joining a query tip to its placement attachment. Interpret it with the selected alignment/model and placement output; it is not percent identity or a species threshold. See [placement workflow](Phylogenetic-Placement.md). |
| Wheelhouse | A local collection of Python distribution wheels for the selected installation. It must cover the target platform, Python ABI, build requirements and chosen extras; possession of some wheels does not prove a complete offline install. See [installation](../docs/INSTALL.md). |
| Virtual environment | An isolated Python interpreter/package environment. Use the same environment for bundle installation and commands, and bind the actual bundle root; isolation alone does not identify which bundle a console launcher resolves. See [prerequisites](Prerequisites.md). |

<!-- Maintenance: this is the reader-facing canonical glossary. Add or revise a definition here when a scan, code or overloaded term enters the bundle, and point other pages here. Keep counts, formulas and status lists tied to their code or schema source. `wiki/Glossary.md` is generated by `tools/sync_wiki_mirrors.py`. 
Maintenance note: version-sync marker for the installed engine 1.9.181.
-->
