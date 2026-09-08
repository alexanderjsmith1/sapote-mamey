# Sapote–Mamey Documentation Protocol
## Instructions for Contributing Claude Instances
**Bundle v9.7.319 · Engine 1.9.111**

> **SUPERSEDED ROUTING NOTICE.** This historical protocol formerly routed new definitions to `comprehensive_glossary.md` and dependency claims to `sapote_mamey_wheel_glossary.md`. Those files are retained snapshots, not current authorities. New or corrected reader-facing definitions go to [`docs/GLOSSARY.md`](../GLOSSARY.md); versioned formulas, command lists, schemas, and dependency facts stay grounded in their current code or schema source.

*This document instructs any Claude instance working on Sapote–Mamey documentation how to contribute entries that are consistent in format, verifiable in content, and structured to merge cleanly with existing documents. Read this entire document before writing a single glossary entry or documentation section.*

---

## 1. What This Protocol Covers

The Sapote–Mamey project maintains a living documentation set consisting of:

1. `sapote_kernel_guide.md` — The kernel architecture, gates, and recent version changes
2. `../GLOSSARY.md` — The one canonical reader-facing term glossary
3. `comprehensive_glossary.md` and `sapote_mamey_wheel_glossary.md` — Superseded snapshots retained for provenance and drift review
4. `large_files_reference.md` — Detailed documentation of all files ≥1 MB
5. This file — The protocol that governs how all of the above are maintained

These documents are designed to be additive. Any Claude instance can open any document, add entries, extend sections, or begin a new section, provided it follows the rules below. The goal is to produce documentation that is functionally useful — that helps a human understand how to improve analysis quality and pipeline efficiency — not documentation that superficially describes the program.

---

## 2. What NOT To Do (The Failure Mode This Protocol Exists To Prevent)

Past file scanning in this project has fallen into two anti-patterns that produce useless documentation:

**Anti-pattern 1: Version number scanning.** Reading files and noting stale version strings, then documenting "file X has version Y." This is not useful documentation. Version consistency is enforced by `tools/sync_version.py`; it is not a human documentation concern.

**Anti-pattern 2: Privacy tier scanning.** Checking whether strain IDs contain "AS-" and noting their public/private status. This is handled by the engine's release-tier machinery. Documenting it in glossaries adds noise without substance.

**Anti-pattern 3: Superficial file description.** Writing "this module does X" where X is a one-sentence paraphrase of the module filename. Every entry must go deeper: what does this module actually compute, what formula does it use, what are its failure modes, how does it interact with other modules, what would go wrong if it malfunctioned?

**Anti-pattern 4: Inference from filenames.** Writing a description of a module's function based on its name rather than its docstring, formula, or actual implementation. If you have not read the source, say so explicitly and do not write a description.

**The test for any entry:** Would this entry help someone: (a) understand why the pipeline produces the output it does, (b) identify when something has gone wrong with that output, or (c) decide how to improve the analysis quality or efficiency? If no, the entry is too thin.

---

## 3. Document Format Rules

### 3.1 Header Block

Every document must begin with:
```markdown
# [Document Title]
**Bundle v[VERSION] · Engine [ENGINE_VERSION] · [build stamp if known]**
*[One or two sentences describing the document's scope and how its entries were derived.]*
```

The version numbers must match the active bundle. The scope statement must be honest about what was and was not read. Example: "All formulas transcribed from `docs/reference/01_Math_Reference_VolI.md`; module descriptions from direct docstring extraction; no values inferred from general knowledge."

### 3.2 Section Headers

Use `##` for top-level sections and `###` for subsections. Sections should be numbered (Section 1, Section 2, etc.) to make cross-references unambiguous across sessions. New sections append to the end of a document with the next sequential number; they do not insert into the middle of an existing section structure.

### 3.3 Glossary Entry Format

```markdown
**[Term]** — [One-sentence definition in plain language, stating what the term means, not what it is called.]

[Body: 2–6 sentences expanding on the definition. Must include at least one of: the formula, the source module, the failure mode, the cross-references to related terms, or the practical consequence of misunderstanding the term. End with a source citation.]
```

If the entry is for a formula or constant, use this format instead:
```markdown
**[Term/Constant]** — [What it measures and why.]

**Formula:** `[exact formula from source]`
**Source:** `[module.py:function_or_symbol]`
**Constants:** [table if multiple related constants]
[2–4 sentences: what the formula produces, edge cases, what changes if inputs change.]
```

If the entry is for a module:
```markdown
**[module_name.py]** — [First line of docstring or functional description.]

[2–5 sentences on what the module computes or manages, which other modules it calls or is called by, what its output looks like, and what fails if it is absent or incorrect. Include source evidence (line numbers, function names) not just "it does X."]
```

### 3.4 Tables

Use markdown tables for: comparison of values, parameter lists, mapping of codes to meanings, lists of patterns. Every table must have a source line immediately below it:
```markdown
*Source: [file and section]*
```

Tables that list patterns from `docs/MARKER_CATALOG.generated.md` must include the pattern count alongside the family count (e.g., "18 families / 121 patterns") and must not modify or summarize the patterns — transcribe exactly as they appear in the source.

### 3.5 Source Citations

Every entry must end with or contain an explicit source. Acceptable forms:
- `Source: module.py:function_name` — for formulas and algorithms
- `Source: docs/DOCUMENT_NAME.md` — for contracts and specifications
- `Source: CHANGELOG.md v9.7.XXX` — for recent changes
- `Source: [file]:L[line_start]–[line_end]` — for specific passages

Never cite "the bundle" generically. Never cite a document you have not read in this session. If you are writing from memory, say "from memory — verify against [file]" rather than asserting it as verified.

---

## 4. How To Scan Files Productively

When you examine a file for documentation purposes, you are looking for:

1. **What does this compute?** Not the name — the actual operation. A function called `score_keywords` scores keywords; but the productive question is: what is the scoring model, what are the weights, what are the edge cases?

2. **What is the failure mode?** Every module has one. `write_nr_overlay` failed by truncating instead of merging (P7a). `antismash_domains` was hardcoded to empty (P7b). `B5_BLASTp_Hits` append was not idempotent (P7c). Documenting the failure mode is more valuable than documenting the happy path.

3. **What does this interact with?** Which modules call this one, which does this one call, what data flows through? `scoring.py` calls `source_scans.py` for CCTT triggers; misidentifying that dependency produces a wrong analysis of when scores change.

4. **How does the output reach the user?** Does it go into `manifest.json`, into a workbook sheet, into a Mode B card section, into a figure? The chain from computation to deliverable is what a scientist trying to reproduce or validate an output needs to trace.

5. **What constants are hard-coded here?** Hard-coded constants are documentation priorities because they cannot be changed without a code edit. The assembly tier thresholds (70/45/20), the corrected-count weights (1/0.5/0.25), the scoring bases (25/20/30), the RG-GMCI tier cutoffs (14/9) — these are all load-bearing numbers that belong in the glossary.

---

## 5. What Belongs in Which Document

**`../GLOSSARY.md`** — The one canonical reader-facing definition source. Add or revise terms there; point to current code/schema for formulas, enumerations, commands, and machine states instead of copying them as version-free prose.

**`comprehensive_glossary.md`** — Superseded drift snapshot. Do not add definitions or treat its formulas and command lists as current.

**`sapote_kernel_guide.md`** — Architecture explanations (why the two-layer design), history (slim kernel → execution slice), gate descriptions, and version-by-version changelog for Sapote-facing changes. If you are documenting something that changed in a recent version, it goes in the kernel guide's Part IV section, most recent first.

**`sapote_mamey_wheel_glossary.md`** — Superseded add-on inventory snapshot. Record current dependencies in their package/installer registries; do not infer runtime use from a staged wheel.

**`large_files_reference.md`** — Files ≥1 MB. If a new large file is added to the bundle or addons, add its entry following the inspection methodology section: run direct Python inspection, report exact byte count, describe structure, describe what the engine does with it.

**New documents** — If a topic is too large for a single section addition and would better stand alone (e.g., a complete BGC class reference, a complete SOP for a specific workflow), create a new document with the standard header block and register it in this protocol document's section 2 list.

---

## 6. Merging Across Sessions

Documents are designed to be merged by appending. The rules:

**Appending to an existing section:** Find the section by its number and heading. Add new entries below the last existing entry in that section. Do not re-sort or re-order existing entries.

**Adding a new section:** Append to the end of the document. Assign the next sequential section number. If the document already has 20 sections, the new one is Section 21.

**Updating an existing entry:** If you have better information than a previous entry (e.g., you found the actual formula for something previously described by analogy), replace the entry body but preserve the term and its format. Add a note: "Updated [version] — [brief description of correction]."

**Retracting an incorrect entry:** If an entry is demonstrably wrong (wrong formula, wrong module attribution, wrong failure mode), do not simply delete it — mark it as retracted: "~~[old content]~~ RETRACTED [version]: [reason]. Correct information: [new content]." This preserves the audit trail.

**Conflict between sessions:** If two sessions produced different descriptions of the same term, keep the one that cites a more specific source (line number beats file name beats "the bundle"). Flag the other as "UNVERIFIED — superseded by [source]."

---

## 7. The Quality Test for Every Entry

Before finalising any entry, ask:

1. Does this entry contain at least one piece of information that cannot be inferred from the term's name alone?
2. Does this entry cite a specific source (file, line, formula)?
3. Would a scientist unfamiliar with this codebase, reading only this entry, understand what they should do differently when they encounter this term?
4. If the module/formula/gate this entry describes was broken, would this entry help diagnose the breakage?

If the answer to any of these is "no," the entry needs more work.

---

## 8. Handling Uncertainty

When you are not certain about an entry's content:

**If you have not read the source file:** Write the entry as a stub — the term, a one-line placeholder ("see [file]"), and a note that it needs verification. Do not invent plausible-sounding content.

**If you have read the source but the source is ambiguous:** Say so. "The formula in `scoring.py:triage_bgcs` (line ~320) appears to apply this weight after the keyword sum, but the ordering is not entirely clear from the source — verify by adding a print statement."

**If you are working from a prior session's memory and the file has not been re-read this session:** Flag it: "From prior session context — verify against `[file]` at session start."

The project's standing doctrine is that a confident but wrong claim is worse than an explicit admission of uncertainty. This applies to documentation as much as to Mode B cards.

---

## 9. Efficiency and Quality Improvement Focus

The primary value of these documents is to help improve the analysis itself. When scanning files, prioritize documenting:

**Efficiency improvement opportunities:**
- Redundant computations (two modules computing the same thing)
- Places where caching would help (repeated antiSMASH JSON parses)
- Batch size limits that are more conservative than necessary (MAX_BATCH was 10, raised to 30 at v9.7.240 after empirical validation)
- Timeouts that fire before valid runs complete

**Quality improvement opportunities:**
- Known false positives in scan patterns (the hglE/hglD PREV-001 enediyne false positive)
- Gates that are documented but lack tests (marked "⚠ test needed" in `docs/TRIGGER_ROUTING.md`)
- Evidence gaps in the confidence vocabulary (what "inferred" means vs. "assumed" in practice)
- Conditions where the scoring model systematically mis-ranks a known chemistry class

**Design decisions that could be revisited:**
- The edge penalty being set to 0.0 (currently dormant, awaiting calibration data)
- The GH19 gap in CGAD (GH19 chitinases in *Streptomyces* are not scanned for)
- The NAPAA exclusion (may need periodic revisit as the ecological literature grows)

Document these as "Open question" entries in the relevant section, not as bugs, unless there is evidence of active misclassification.

---

## 10. Session Start Protocol

At the start of any documentation session:

1. Search conversation history for the most recent documentation session to avoid duplicating work.
2. Read the header block of each target document to confirm the current version number matches the active bundle.
3. Identify the last entry in each section to know where to append.
4. Read this protocol document in full before writing.

At the end of any documentation session:

1. State which sections were added to or modified and which files they are in.
2. State what was not covered (what would be the logical next section to write).
3. Provide the standard CDSW next-paths list.

---

## 11. Document Version Tracking

Each document should include, at the end of its header block or as a footer, the session that last updated it:

```markdown
*Last updated: [YYYY-MM-DD] · Session: [brief description] · Bundle: [version]*
```

This allows future sessions to immediately see which session contributed which content and to request conversation history from that session when a correction is needed.

---

*This protocol was established 2026-07-09 during the initial documentation campaign. It supersedes any informal documentation guidelines from prior sessions. All contributing Claude instances should treat this document as authoritative for format and process, and the bundle's own source files as authoritative for content.*

---

## 12. Worked Examples — Good vs Thin Entries

The following pairs illustrate the quality difference between entries that pass the Section 7 quality test and entries that do not.

### Example pair 1: Module documentation

**Thin (fails quality test):**
> **figures_sapote.py** — Sapote-layer figure generation module. Produces figures from triage board data.

This fails because: "Sapote-layer figure generation" is derivable from the filename. "Produces figures from triage board data" is technically correct but names no specific figure, no formula, no failure mode, and no source.

**Substantive (passes quality test):**
> **figures_sapote.py** — Deterministic figure module that produces four reader-facing priority figures: `_8c_fig_dapr_scatter.png` (AB vs AF scatter, one point per BGC), `_8d_fig_ab_ranked.png` (top 30 BGCs by AB score), `_8e_fig_af_ranked.png` (top 30 by AF score), `_8f_fig_funnel.png` (claim-safety triage funnel). All read only from `manifest.json` and the triage board CSV — no LLM judgment required. Thresholds: `LEAD_AB_MIN = 70.0`, `LEAD_AF_MIN = 44.0`, `RANK_TOPN = 30`. Pure-saccharide BGCs excluded via `mamey/figure_policy.py:is_pure_saccharide()` — a single shared gate. Failure mode: if the triage board is empty (VERY_POOR assembly with all BGCs downgraded), these figures render with empty axes. Source: `mamey/figures_sapote.py`, docstring lines 1–14 and constants at module level.

This passes because it names the specific output files, the data source, the thresholds, the cross-module dependency, and the failure mode.

### Example pair 2: Formula documentation

**Thin:**
> **Corrected BGC count** — A count that is corrected to account for fragmented BGCs.

This fails because: it describes what the term means without saying how it is computed, what the weights are, or why those weights were chosen.

**Substantive:**
> **Corrected BGC count** — A fractionally-discounted BGC count that accounts for partial evidence from truncated clusters. Formula: `corrected = round(I + 0.5×E + 0.25×F, 2)` where I = Interior count, E = Edge count, F = Full-contig count. The weights encode partial evidence: Interior clusters count fully (1.0); Edge clusters, truncated at one boundary, count half (0.5); Full-contig clusters, presumed truncated at both ends, count a quarter (0.25). The raw count `I + E + F` is always reported alongside — the discount is transparent. Invariant: corrected ≤ raw always; violation signals a coordinate or edge-status bug (was the observed failure that triggered the circular-replicon fix at v9.7.87). Source: `mamey/assembly.py:corrected_bgc_count`.

### Example pair 3: Failure mode documentation

**Thin:**
> The enediyne guard prevents false positives.

This fails because: it names the guard but not what it guards against, how it distinguishes real from false, or what happens if it fails.

**Substantive:**
> **Enediyne guard** — Prevents the hglE/hglD glycolipid ketosynthase domain from being scored as an enediyne discovery. The hglE-KS domain (heterocyst glycolipid synthase) shares sequence similarity with the enediyne KS used in CCTT T43-ENE detection — a false-positive class documented as PREV-001. The guard: (1) checks whether the `enediyne` keyword fired on a locus that also contains `hglE` or `hglD` annotation tokens; (2) if so, strips the +18 novelty credit and records the veto; (3) if a genuinely named-enediyne KCB anchor is also present, emits a neutral `[E-signal]` note without novelty adjustment. The BSL-2 per-BGC flagging doctrine is retired — a selective biosafety flag on one BGC class provides false reassurance and is inconsistent with chemical handling governed by lab SOPs. Source: `mamey/scoring.py:triage_bgcs`, `docs/MARKER_CATALOG.generated.md:CCTT_VETOES section`.

---

## 13. Figure Documentation Format

When documenting figures, use this format:

```markdown
**[_8X_fig_NAME.png]** — [One sentence: what the figure shows and what data it is derived from.]

**Data source:** [which package file(s) are read]
**Module:** [mamey/figures_XXX.py:function_name]
**Companion CSV:** [_8X_fig_NAME_data.csv — column headers]
**Failure mode:** [what causes this figure to be blank or absent]
**Policy:** [any standing rules applied, e.g. saccharide exclusion]
```

Example:

**_8h_fig_cctt_map.png** — Horizontal bar chart of CCTT diagnostic-trigger prevalence: one bar per T43-XXX family, bar length = number of BGCs in this strain carrying that trigger, sorted by prevalence.

**Data source:** `_4_triage_board.csv` (column `CCTT_triggers`, comma-separated trigger codes per BGC)
**Module:** `mamey/figures_extra.py:fig_cctt_map`
**Companion CSV:** `_8h_fig_cctt_map_data.csv` — columns: `cctt_trigger`, `bgc_count`, `bgc_ids`
**Failure mode:** Empty if no CCTT triggers fired in this strain (a valid result for gene-poor VERY_POOR assemblies). Also empty if the triage board column `CCTT_triggers` is blank for all rows (check that source_scans ran).
**Policy:** Pure-saccharide exclusion applies (BGCs excluded from figure population).

---

## 14. Session Tracking Table Template

At the end of each documentation session, contribute this table to the target documents:

```markdown
| Session date | Bundle version | Sections added/modified | Files modified | What remains |
|---|---|---|---|---|
| 2026-07-09 | v9.7.241 | §21–§25 (comprehensive_glossary), Parts VI–VII (kernel_guide), Appendices A–C (wheel_glossary), §Degradation+§Checksums (large_files), §12–§14 (cross_chat_protocol) | 5 documents | §26+ in glossary: BLASTp store fields, A-domain substrate specificity, resistance self-protection taxonomy |
```

This table allows the next session to immediately understand what was covered and what to pick up next, without reading the full conversation history.

---

*Last updated: 2026-07-09 · v2 additions (sections 12–14) · Bundle v9.7.319*

---

## 15. Document Registry — Current (v9.7.246)

Section 1 listed five documents. The set is now **ten**. This table supersedes it.

| # | Document | Current version | Scope |
|---|---|---|---|
| 1 | `sapote_kernel_guide.md` | v3 | Architecture, kernel history, gate stack, version-by-version changes, lineage split |
| 2 | `../GLOSSARY.md` | canonical | Single reader-facing term authority; versioned details cite code/schema |
| 3 | `comprehensive_glossary.md` / `sapote_mamey_wheel_glossary.md` | superseded | Historical drift and inventory snapshots; no new definitions |
| 4 | `operational_reference.md` | v4 | Installation, run sequence, SOPs, BLASTp, Bert Mode, live-run receipts |
| 5 | `development_issues_compendium.md` | v3 | Documented bugs with root cause, fix, and prevention rule |
| 6 | `tools_reference.md` | v3 | Every script under `tools/`, with flags and live receipts |
| 7 | `large_files_reference.md` | v2 | Every file ≥ 1 MB; structure, degradation, checksums |
| 8 | `math_reference_vol1.md` | v1 | Core engine formulas: counting, assembly tiers, AB/AF/novelty, guards, RG-GMCI, completeness |
| 9 | `math_reference_vol2.md` | v2 | Subsystem formulas: CCTT, architecture-first, KCB/RiQ, compound class, rescue, enrichment, **Cluster G** |
| 10 | `cross_chat_doc_protocol.md` | v3 | This file |

**New documents must be registered here.** A document not in this table is invisible to the next session.

---

## 16. Where New Content Goes — Decision Table

Ambiguity about placement is the commonest cause of duplicated entries across sessions. Use this table before writing.

| You have… | It goes in… | As… |
|---|---|---|
| A bug with a root cause and a fix | `development_issues_compendium` | A new entry in the matching Group, or a new Group if the class is new |
| A defect class that has recurred ≥ 3 times | `development_issues_compendium` | Its own Group, with a table of instances and a diagnostic |
| A new or corrected reader-facing term | `../GLOSSARY.md` | One canonical definition plus a pointer to current code/schema for versioned details |
| A new gate | `sapote_kernel_guide` Part VIII **and** `tools_reference` | The gate stack table + a section on the tool that enforces it |
| A new `tools/` script | `tools_reference` | A section with docstring, flags, exit codes, and a **live receipt** |
| A version's changes | `sapote_kernel_guide` Part IX | Most-recent-first, one subsection per version |
| A **core** formula (counting, tiers, AB/AF/novelty, guards, RG-GMCI) | `math_reference_vol1` | The matching section, with `module.py:symbol` citation |
| A **subsystem** formula (CCTT, architecture, KCB/RiQ, class, rescue, enrichment, crosswalk/dedup/merge/gates) | `math_reference_vol2` | The matching Part (A–G) |
| A command sequence or protocol | `operational_reference` | A numbered section |
| A file ≥ 1 MB | `large_files_reference` | An entry with byte count, structure, and degradation behaviour |
| An add-on dependency | `pyproject.toml`, `mamey/data/companion_tools.json`, or the controlling installer/registry | A machine-readable dependency or optional-tool update; do not update the superseded wheel snapshot |

**If it fits two, put the substance in one and a one-line cross-reference in the other.** Do not duplicate prose. A reader who follows the cross-reference is better served than a reader who finds two entries that have drifted apart.

---

## 17. The Live-Receipt Requirement

**Any claim about what a tool does must be accompanied by output from having run it.** This is the strongest single quality rule in this protocol, and it is the one most often skipped.

**Not acceptable:**
> `tools/file_atlas.py` scans the source tree and reports orphan modules.

**Acceptable:**
> **Live receipt on bundle v9.7.246:**
> ```
> 280 files under mamey/ and tools/
> 74,981 total lines
> 35 orphan candidates (no importer, no CLI verb, no test)
> 57 files no test names at all
> ```

The receipt does three things the description cannot. It proves the tool runs in this bundle. It pins the numbers to a version, so a future reader knows whether they are stale. And it exposes the tool's actual output format, which is what a user will see.

**If you cannot run the tool**, say so explicitly — *"not run this session; flags read from `--help`"* — and do not present inferred output as observed output. This is the same discipline the `PHANTOM_LOCUS` lint exists to enforce on Mode B cards: **a true example presented as an observation of a thing you did not observe is a fabrication, however true it is elsewhere.** The rule applies to documentation exactly as it applies to science.

---

## 18. Anti-Pattern 5: The Vivid Foreign Example

Added after v9.7.246, where a genuine per-gene BLASTp result from *Amycolatopsis* sp. NPDC004378 was templated into 74 Mode B cards belonging to two other strains, and every guard passed it.

**The pattern:** a real, specific, illustrative example — a locus tag, a score, an accession, a BGC id — is embedded in a template, a glossary entry, or a protocol document. It is true. It illustrates its point perfectly. And it belongs to a different subject than the one the reader is looking at.

**Why it survives review:** a reviewer checks whether the example supports its point. It does. Nobody checks whether the example belongs to the subject in front of them. **A vivid, true example from the wrong organism is more dangerous than an obviously wrong one.**

**The rule for documentation.** An example may carry a concrete identifier only when the source of that identifier is named in the same sentence. Write:

> Verified against the real AS-XXX package: 758 loci loaded, `ctg12_71` not among them.

Not:

> `ctg12_71` was overturned by BLASTp.

The first is an observation with a subject. The second is a claim floating free of the organism it came from, ready to be copied into a document about a different strain.

**The rule for templates.** Templates may carry methodology, instructions, and structure. **Templates may not carry findings.** If a concrete example is needed, cite it by path and name the organism, with an explicit instruction not to cite its identifiers in the authored text — exactly as `modeb_template_emitter._section_body(4)` now does.

---

*Last updated: 2026-07-09 · v3 additions (Sections 15–18) · Bundle v9.7.246*
