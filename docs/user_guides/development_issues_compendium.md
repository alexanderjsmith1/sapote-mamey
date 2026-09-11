# Sapote–Mamey Development Issues Compendium
## Documented Bugs, Misidentifications, and Design Failures
**Bundle v9.7.241 · Engine 1.9.111**
Hamilton, Ontario

*Source: `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md` (645 lines). Content is a curated summary of entries from the living development log, arc v9.7.102–v9.7.241 (engine 1.9.98–1.9.111). Entries that were resolved are documented with their fix; unresolved items (if any) are noted. Root causes and prevention rules are the primary value — not the incidents themselves.*

---

## How To Use This Document

Each entry names: what went wrong, how it was discovered, the root cause, the fix, and what the prevention rule is going forward. Severity follows the patch chat convention: **Must-fix** (blocks release), **High** (degrades science or breaks user-facing workflow), **Medium** (correctness issue with workaround), **Low** (doc gap, cosmetic, or latent).

Entries are grouped by theme. Read the prevention rules as standing doctrine for any new code or analysis.

---

## Group 1: PDF Compiled Report Issues

### PDF-1: Overlapping text on first section page
**Severity:** High · **Fix in:** v9.7.148c

Mini-header blocks copied from the cover page into subsequent sections produced three simultaneous text layers on the first body page (YAML `\maketitle` + automatic running header + body text header). The page became unreadable.

**Prevention:** Section bodies begin directly with the section heading (`# 1. Synopsis`). No repeat of strain/date/bundle metadata as body text. The running header is placed by the renderer automatically.

---

### PDF-2: Dark blue background from wkhtmltopdf dark mode inheritance
**Severity:** High · **Fix in:** v9.7.148

wkhtmltopdf inherits dark-mode CSS from the host system environment. On a dark-mode machine, PDFs render with dark backgrounds. The pipeline's correct PDF path is: `Markdown → tools/md_to_pdf.sh → pandoc → xelatex`.

**Prevention:** `wkhtmltopdf` is banned for compiled report rendering. Always produce Markdown first; the Markdown file is the canonical deliverable. The PDF is a presentation copy.

---

### PDF-3: Compiled report was Mode B cards only (not complete deliverable)
**Severity:** High · **Fix in:** v9.7.148

A testing session produced a 7-page "Mode B Report" and treated it as the compiled analysis deliverable. It contained only Mode B cards — no layperson guide, no figures, no ecology, no fermentation guidance, no triage board.

**Prevention:** The compiled report has 14 required sections in a fixed build order: Cover → Executive summary → Layperson guide → Assembly summary → Triage board → Figures → Ecological synthesis → Priority lead deep-dives → Complete Mode B cards → §21–§30 extensions → BLASTp evidence table → Fermentation guidance → Wet-lab matrix → Outstanding actions → Methods. Target length for a 13-BGC strain with 10 cards: 40–80 pages.

---

### PDF-4: Blank pages from double section breaks
**Severity:** Medium · **Fix in:** v9.7.148c

Each `---` horizontal rule in Markdown renders as `\clearpage` in LaTeX. A pattern using two `---` before each section produced two forced page breaks, creating near-blank pages at every section boundary — 16 wasted pages out of 111 (14%).

**Prevention:** Single-break pattern only:
```
[last content line]

---

# 3. Chapter — BGC Landscape

[first content line]
```
No dedicated section title pages. No double rules. No explicit `\clearpage` or `\newpage`.

---

### PDF-5: 324 bare BGC ID instances in 111-page report
**Severity:** High · **Fixed in:** v9.7.148b (rule), v9.7.148c (scan enforcement)

An audit found 383 bare BGC ID instances (`BGC028`, `BGC020` etc.) in the AS-XXX compiled report. 324 were in prose sections (violations); 28 were in the TOC (acceptable); 4 were cover summary table entries (acceptable). The node/region citation rule existed as a soft guideline but was not enforced in prose outside triage tables.

**Prevention:** Hard rule (§15 of execution slice): every BGC instance in prose carries its node citation. Required formats:
- First mention in a section: `BGC007 (NODE_1_length_406707_cov_83 · region001)`
- Subsequent mentions within same section: `BGC007 (NODE_1 · r001)`
- Exclusion lists: `NAPAA (BGC023 · NODE_4 · r001)` — not `NAPAA (BGC023)`

Before PDF rendering: run a pre-delivery scan for bare BGC ID patterns across the entire compiled Markdown source. The `node_citation_map.json` (W7 output in every package) pre-builds the `{BGC007: NODE_1... · region001}` lookup.

---

### PDF-6: Hand-written TOC page numbers up to 53 pages wrong
**Severity:** High · **Fix in:** v9.7.148d

The AS-XXX compiled report (115 pages) had page numbers that drifted progressively as the document grew. The Outstanding Work section was listed as page 60; it actually started on page 113 (+53). Users following the TOC could not find major sections.

**Root cause:** TOC was hand-written with estimated page numbers before finalising content.

**Prevention:** Use pandoc's automatic TOC via YAML front-matter:
```yaml
---
toc: true
toc-depth: 2
---
```
This inserts `\tableofcontents` at the LaTeX level, computed correctly after two-pass compilation. Never hand-write a TOC. If no LaTeX renderer is available, omit the TOC entirely — missing is better than wrong.

---

### PDF-7: Overclaims in layperson guide plain-English descriptions
**Severity:** Medium · **Fix in:** v9.7.148c

The AS-XXX layperson guide contained compound identity claims: "produces a structurally distinct analogue of totopotensamide," "the compound is secreted into the growth medium," "the compound is also heavily methylated." Plain English is inherently declarative; writers slip from capacity language to identity claims.

**Claim-safety line for layperson text:**
- ✅ Class-level: "produces siderophore-type iron-grabbing molecules"
- ✅ Analogy to known: "has genes for making polyketide antibiotics, a class that includes erythromycin"
- ❌ Compound identity: "produces totopotensamide" or "produces a structurally distinct analogue of X"
- ❌ Implied isolation: "the compound is secreted" (implies we know what the compound is)

---

## Group 2: BGC Class Misidentification

### MISID-1: BGC044 ranthipeptide → mycofactocin (redox cofactor, not antibiotic)
**Severity:** High · **Discovered in:** v9.7.146

BGC044 (AS-XXX, NODE_73) was assigned as ranthipeptide across multiple analysis sessions. Full §1–§20 Mode B cards and §21–§30 extensions were produced under this assumption. All were wrong. BGC044 produces mycofactocin — a redox cofactor RiPP used in electron transfer.

**Root cause:** Analysis was done from raw antiSMASH GBK files before running the Mamey TIGRFAM scan. TIGR03997 (MftE, HMHP hydrolase — a mycofactocin-specific enzyme) was annotated under a name that superficially resembled an RRE domain.

**Seven diagnostic markers that were present:**
TIGR03969 (MftA precursor), TIGR03968 (MftB, RRE cognate to MftC), TIGR03967 (MftC radical SAM maturase), TIGR03996 (MftD FMN-dependent oxidoreductase — **DIAGNOSTIC**), TIGR03997 (MftE HMHP hydrolase — **DIAGNOSTIC**), TIGR03965 (MftF glycosyltransferase), TIGR03964 (MftF/creatininase). SPASM domain (TIGR04085) was also present — but SPASM occurs in both ranthipeptide AND mycofactocin pathways and is not discriminating alone.

**Disambiguation rule (§14 of execution slice):** when TIGR03967 + TIGR03996 + TIGR03997 co-occur on a contig, the class is mycofactocin regardless of TIGR04085 presence.

**Lesson:** Mamey-first is a hard gate. Working from raw GBK files before the Mamey package is sealed causes systematic class errors that compound through all downstream analysis — Mode B cards, DAPR leads, fermentation guidance are all wrong.

---

### MISID-2: BGC022 Linocin_M18 bacteriocin → encapsulin nanocompartment
**Severity:** Medium · **Discovered by:** BLASTp validation

BGC022 (AS-XXX) was initially assigned Linocin_M18 bacteriocin. BLASTp of the shell protein gene at 94.2% identity to *Pseudonocardia sulfidoxydans* encapsulin shell protein revealed it is an encapsulin nanocompartment with hemerythrin cargo.

**Root cause:** The Linocin_M18 Pfam domain is structurally homologous to encapsulin shell proteins — antiSMASH identifies the fold correctly but cannot distinguish biological context. Accepting the domain-level call as the class call without BLASTp confirmation was the error.

**Note:** This reclassification elevated the BGC's interest (encapsulins are ecologically relevant for ROS management and potential direct antimicrobial activity), not downgraded it.

---

### MISID-3: BGC036 terpene/carotenoid → SUF operon (primary metabolism)
**Severity:** Medium · **Discovered in:** v9.7.146 Mamey run

BGC036 was reported by antiSMASH as a terpene/carotenoid BGC. The Mamey TIGRFAM scan identified SUFBD (TIGR01980/01981), ABC transporter (TIGR01978), aminotransferase (TIGR01979), and NifU (TIGR01994) — the complete iron-sulphur cluster assembly pathway (sufBCDSU). Primary metabolism, not secondary metabolite.

**Rule:** TIGRFAM-based primary metabolism designation is authoritative over antiSMASH product class calls when they conflict.

---

## Group 3: Test Infrastructure

### TEST-1: Dummy SHA256 checksums in test fixture
**Severity:** Medium · **Fix in:** v9.7.148a

`_write_minimal_package()` wrote `"dummy"` as the SHA256 value for every file. The real checksum verification gate was added to `mamey/validate.py` in v9.7.145b. From that version onward, the test correctly failed with checksum mismatch errors on its own synthetic package.

**Fix:** `_write_minimal_package()` now computes real SHA256 hashes: `hashlib.sha256(path.read_bytes()).hexdigest()` for both `manifest.json` and `checksums_sha256.txt`.

**Prevention:** When adding a new validation gate to production code, audit all test fixtures that generate synthetic packages — they must be updated simultaneously.

---

### TEST-2: Missing f-string prefix — literal output of `{len(results)}`
**Severity:** Must-fix · **Fix in:** v9.7.148a

In `mamey/cli.py`, a multi-strain gold figure skip message was:
```python
print("  Gold domain figures: SKIPPED — only 1 of {len(results)} strains is gold mode")
```
Users saw the literal string `{len(results)}` instead of the count. The bug was in an `elif` branch that only fires when exactly one of N strains has a gold-mode package — an edge case with no automated test coverage.

**Prevention:** f-string bugs in infrequently-executed branches are found only by coverage-guided testing or by hostile audit. Add branch-coverage tests for multi-strain edge cases.

---

### TEST-3: Gene-mention regex matched wrong patterns (false SHALLOW grading)
**Severity:** High · **Fix in:** v9.7.111

`mode_b_quality_gate`'s `_RE_LOCUS` regex used `\d{4,6}` to detect gene mentions. Real antiSMASH locus tags are `ctgN_M` format where M is typically 1–3 digits. The regex matched 0% of real locus tags, causing genuine deep Mode B cards to grade SHALLOW on every strain tested (5 strains, 3,916 locus tags all missed).

**Fix:** `_RE_LOCUS` rewritten to match the structural `ctgN_M` format (any suffix width) plus RiPP-precursor class suffixes. 100% match / 0 false-positive across the validation set.

---

## Group 4: Version Synchronisation

### VERSYNC-1: sync_version.py regex breaks on letter-suffix versions (9.7.148a, b, c...)
**Severity:** High · **Fix in:** v9.7.148b

`tools/sync_version.py` used `re.compile(r'\d+(?:\.\d+)*')` to match version strings. This pattern matches only digits and dots. When the bundle version is `9.7.148a`, the pattern matches `9.7.148` inside `9.7.148a`, then the replacement appends the suffix `a` — producing `9.7.148aa`. On the next run: `9.7.148aaa`. The corruption accumulates with every sync run.

Affected files: TAG, docs/BUNDLE_CAPABILITIES.md, RELEASE_MANIFEST.md, docs/PLAYBOOK.md, prompts, and AGENTS.md bootstrap files.

**Fix:** All 44 `re.compile()` version patterns updated from `\d+(?:\.\d+)*` to `\d+(?:\.\d+)*[a-z]*`. Two PLAYBOOK-specific patterns updated from `[\d._]+` to `[\d._]+[a-z]*`. The `[a-z]*` (greedy, zero or more) consumes the entire suffix in one match.

**Prevention:** If your versioning scheme can produce letter suffixes, test `sync_version` against them before release. The fix is one character per pattern, but the corruption it prevents is significant — every affected file needs manual repair.

---

## Group 5: BGC Node/Contig Citation Enforcement

### CITE-1: 79 bare BGC IDs in analysis report prose
**Severity:** High · **Fix in:** v9.7.148b

The AS-XXX full analysis report had 79 lines with bare BGC IDs in prose sections, §28/§30 evidence ledgers, exclusion lists, cross-reference sentences, and ecological synthesis. The node citation rule existed as a soft guideline but had no mechanical enforcement.

**Impact:** BGC IDs are Mamey-internal bookkeeping. A collaborator cannot locate `BGC007` in the assembly or antiSMASH HTML without the node and region. The node citation is the actual locus identifier.

**Fix:** Execution slice §15 added hard enforcement with required formats, explicit violation examples, and a mandatory pre-delivery scan instruction. `node_citation_map.json` added as a W7 output in every package for lookup automation.

---

## Group 6: BLASTp and Sequence Analysis

### BLASTP-1: bgc_blastp_panel produces cohort-wide pools, not per-BGC batches
**Severity:** Medium · **Fix in:** v9.7.148

`bgc_blastp_panel` ran automatically but produced cohort-wide FASTA pools (20 proteins per file, all BGCs mixed), not per-BGC batches ready to submit. Users had to make a separate explicit request to get the per-BGC FASTA batches they needed.

**Fix:** New `mamey/modeb_blastp.py` module and `mamey modeb-blastp` CLI command. Deduplicates by locus_tag, writes per-BGC batches to `<pkg>/modeb_blastp/<BGC_ID>/`. §16 completion in the execution slice now triggers `mamey modeb-blastp` — FASTA emission is required, not optional.

---

### BLASTP-2: Large protein (3,049 aa) may exceed NCBI web BLASTP limit
**Severity:** Low · **Documented in:** v9.7.147

ctg94_18 (BGC050, AS-XXX) at 3,049 aa may be rejected by NCBI web BLASTP (practical limit ~2,500 aa per individual protein).

**Mitigation:** Split at domain boundaries into ~1,000 aa parts and submit as batches 10a, 10b, 10c. Domain boundaries for a 3-module PKS are approximately at residues 1–1,000 (loading module), 1,001–2,000 (first extension), 2,001–end (second extension).

---

## Group 7: Figure Generation

### FIGURE-1: Figures not produced automatically in capped-session mode
**Severity:** High · **Fix in:** v9.7.148

`--chatgpt-safe` (now `--capped-session`) sets `--brief none`, suppressing all figure rendering. The package contained `NO_FIGURES_RENDERED.md` but the post-MAMEY_COMPLETE handback did not detect this and trigger render-figures before presenting outputs. Users received packages with no figures.

**Fix:** If `NO_FIGURES_RENDERED.md` is present in the package, run `python -m mamey render-all-figures --package <pkg>` before presenting the handback. The session is not complete until figure rendering is attempted.

---

### FIGURE-2: Gold figure suite (F01–F15) existed but never fired automatically
**Severity:** Medium · **Fix in:** v9.7.148

`cohort_figures.py` implements the full F01–F15 domain heatmap and PCA figure suite. Single-strain gold runs never called `figs_single()`. Multi-strain runs called `cohort_figures_bridge` (RGGMCI-focused) but not `cohort_figures.generate()` (the F-series). Users had to request gold figures explicitly every time.

**Fix:** Two non-blocking triggers added to `mamey/cli.py`: one fires `figs_single()` after a single gold-mode run; one fires `figs_multi()` after a multi-strain gold package set. Both are wrapped in try/except so a figure generation failure never blocks the main run output.

---

## Group 8: Scoring and Scientific Accuracy

### SCORE-1: KCB score taken as product identity
**Severity:** High · **Documented in:** ONLINE_BLASTP_PROTOCOL

BGC006 card anchored to colibrimycin (KCB score 3734) as a class precedent. The KnownClusterBlast image showed colibrimycin sharing only a handful of genes — a partial sub-module hit, not cluster identity. High aggregate KCB score with low gene coverage is not a compound anchor.

**Rule:** Never state a KCB anchor without stating its gene coverage. "KCB top hit: colibrimycin (3734, 3/22 proteins)" — not "similar to colibrimycin."

---

### SCORE-2: antiSMASH Pfam calls trusted without per-gene BLASTp validation
**Severity:** High · **Documented in:** ONLINE_BLASTP_PROTOCOL

On BGC006 (AS-XXX), BLASTp overturned two of ten antiSMASH domain calls:
- `ctg12_71`: antiSMASH Beta-lactamase → BLASTp EstA serine hydrolase / esterase (78% id). The "self-resistance β-lactamase" read was wrong.
- `ctg12_21`: antiSMASH Phenol_Hydrox → BLASTp ferritin-family protein (97% id).
A third call (`ctg12_74`: antiSMASH Antibiotic_NAT) was sharpened from generic annotation to named AAC(3) aminoglycoside N-acetyltransferase (77% id) — not overturned but substantially improved.

**Rule:** Per-gene BLASTp is the default for every Mode B lead BGC. Domain calls are hypotheses, not assignments. §4, §8, §27, and §28 are authored *after* BLASTp returns, not before.

---

### SCORE-3: KCB kcb_top genome-self-hit
**Severity:** High · **Fix in:** v9.7.22

When a strain's own genome is in the nr reference database, its own BGCs match themselves and receive artificially high KCB scores. This inflated the novelty penalty (`kcb_cumulative > 10,000 → novelty −15`) and misidentified BGCs as "known clusters" when they were simply the strain itself.

**Fix:** Self-hits are filtered during KCB scoring. The filter identifies hits where the top hit organism matches the query strain's own species.

---

### SCORE-4: Over-merge banner misassignment (P1, v9.7.240)
**Severity:** High · **Fix in:** v9.7.240

The `_over_merge_facts` function matched `predicted_polymers.csv` on the bare contig name, never comparing the region number. Every BGC sharing a contig with an over-merged region inherited the wrong banner — 13 wrong banners generated instead of 7 correct ones on the AS-XXX analysis.

**Rule:** Over-merge banners must cite specific node·region identifiers, not just node names. A banner on BGC008 that carries the same merge signature as BGC009 and BGC010 (which share a contig) is the P1 pattern.

---

### SCORE-5: `authored_verify` aliased wrong field for protocluster count (P2, v9.7.240)
**Severity:** Medium · **Fix in:** v9.7.240

`authored_verify` aliased `single_protocluster_count` onto `protocluster_count`. These fields are different for hybrid BGCs where a single region contains multiple protoclusters (BGC041 in AS-XXX was the specific case — the alias caused the wrong count to be reported). Fixed by reading the correct field directly.

---

### SCORE-6: UMED registry patterns unanchored → 14 false LanT_C39 hits
**Severity:** Medium · **Fix in:** v9.7.240 (P3)

UMED patterns for the LanT_C39 transporter-peptidase family were unanchored (no word boundary enforcement). The pattern matched substrings inside unrelated gene names, producing 14 false hits out of 15 total across the AS-XXX BGC set. Only 1 real LanT_C39 hit after P3 anchoring.

**Rule:** UMED patterns (and all source scan patterns) must use word-boundary or negative-lookbehind anchoring. Test against real genomes, not just synthetic fixtures, before deploying a new pattern.

---

## Group 9: Multi-Chat Coordination Failures

### COORD-1: sapote_workflow.py false-PASS on empty marker files
**Severity:** High · **Fix in:** v9.7.237

Several W-step checks in `sapote_workflow.py` tested for file existence only, not file contents. Files that were created but empty (or containing placeholder text) reported PASS. The gate was reading a marker file's existence as evidence of completion.

**Prevention:** Every gate reads the actual artifact, checks required fields, and reports PASS only when those fields are populated. File existence is necessary but not sufficient for a PASS. This is the "verify against the real artifact, not a proxy" principle stated explicitly.

---

### COORD-2: verify-modeb checking skeleton rather than authored file
**Severity:** Medium · **Documented in:** CLAUDE_START_HERE

The `guide_quality_gate` inside `mamey guide` validates the skeleton's structure (re-derived from the package). The skeleton always passes because it is produced by the engine. `verify-guide` (the separate command) validates the authored file. Reporting "guide validation passed" based on the skeleton gate is a false positive.

**Prevention:** Never report guide or Mode B validation as complete unless `verify-guide` or `verify-modeb` ran on the actually-authored `.md` file, not on the template skeleton.

---

### COORD-3: isolate-giants shredded BGC groups into singletons (P4, v9.7.240)
**Severity:** Medium · **Fix in:** v9.7.240

The `isolate-giants` function was splitting correctly-identified BGC merger groups into singletons before the RGGMCI reconstruction pass. BGC groups that were correctly identified as merged regions were being broken apart before the evidence that formed them could be preserved.

---

## Group 10: Evidence Store and Persistence

### PERSIST-1: P7a overlay write truncation (43% gene loss)
**Severity:** High · **Fix in:** v9.7.241

`write_nr_overlay()` opened the output CSV in `"w"` mode. Each BLASTp ingest round erased the previous round's data for any BGC it touched. On AS-XXX: 877 genes submitted, 504 retained (43% loss). BGC042 worst case: 44 → 7 genes retained. All per-BGC identity scores for affected BGCs were based on the 44% of data that survived the last round.

**Fix:** Opens in merge mode keyed on `locus_tag`; higher bitscore wins collision. Post-patch: 877/877 for AS-XXX.

**Diagnosis:** compare gene count in the overlay file against the count of proteins submitted to BLASTp for that BGC. If below 100%, suspect write-mode bug.

---

### PERSIST-2: P7b antismash_domains hardcoded to empty string
**Severity:** High · **Fix in:** v9.7.241

`antismash_domains` was hardcoded to `""` on the `ingest-blastp` path. `reconcile("", hit_def)` could only return `REVIEW` — the entire CONFIRM/REFINE/OVERTURN discrimination column carried no signal for any BLASTp campaign run through the ingest path.

**Diagnosis:** if the `agreement` column in the overlay CSV shows 100% `REVIEW`, suspect hardcoded `antismash_domains`. The expected distribution for a typical actinomycete BGC is roughly 60–70% CONFIRM, 20–30% REFINE, 5–15% OVERTURN.

---

### PERSIST-3: P7c B5_BLASTp_Hits append not idempotent
**Severity:** Medium · **Fix in:** v9.7.241

Re-ingesting the same Hit Table multiplied rows (150 → 300 → 450 on three ingests). The append was not keyed on any unique combination.

**Fix:** Keyed on `(strain, query_locus, subject_acc, hit_rank, q_start, q_end)`. `duplicates_skipped` returned in result.

**Diagnosis:** count rows before and after a second ingest of the same Hit Table. For an idempotent operation, count should not change.

---

## Summary: Standing Prevention Rules

These rules are derived from the above issues and apply to all new code, analysis, and documentation:

1. **Mamey-first is a hard gate.** Never author Mode B from raw GBK files before the Mamey package is sealed. Class errors from pre-Mamey analysis compound through all downstream work.

2. **Per-gene BLASTp before Mode B §4.** antiSMASH domain calls are hypotheses, not assignments. BLASTp validates or overturns them. §4 is authored after BLASTp, not before.

3. **Verify against the real artifact, not a proxy.** A gate that checks file existence, not file contents, is not a gate. A template skeleton always passes its own quality gate — it has no authored content to fail.

4. **Write-mode vs merge-mode.** Any multi-round write path that opens an output file in `"w"` mode will truncate on every round after the first. Merge paths must key on a unique identifier and use `"a"` or read-merge-write.

5. **Word-boundary anchoring for all scan patterns.** Unanchored patterns match substrings and produce false positives at rates that scale with genome size. Every new pattern must be tested against a real genome before deployment.

6. **Automatic TOC, never hand-written.** Page number drift in hand-written TOCs is unbounded as the document grows. Use pandoc's `toc: true` YAML. If no renderer is available, omit the TOC.

7. **version regex must cover letter suffixes.** A versioning scheme that uses letter suffixes (9.7.148a, b, c) requires that sync_version's patterns use `[a-z]*` at the end. One character prevents file corruption on every cut.

8. **Node/region citation on every BGC instance in prose.** Bare BGC IDs without node/region citations are ambiguous outside the package that generated them. The node/region is the actual locus identifier.

9. **SHA256 checksums in test fixtures must be real.** Dummy checksums in test packages will fail any checksum validation gate added later. Compute real hashes from the fixture content.

10. **Single-session TIGRFAM scan before class assignment.** SPASM domains appear in both ranthipeptides and mycofactocin pathways. MftD + MftE co-occurrence is definitive for mycofactocin. Class-specific diagnostic combinations must be checked before accepting antiSMASH's class label.

---

*Source: `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md`, arc v9.7.102–v9.7.241. Compiled 2026-07-09 · bundle v9.7.241.*

---

## Group 11: Known Calibration Reference Cases

*These entries use the CALIBRATION_CORPUS (known-compound BGCs) to document where the scoring model behaves correctly vs. where it requires human judgment. Source: `docs/CALIBRATION_CORPUS_KNOWN_BGCS.md` and live teicoplanin run 2026-07-09.*

### CAL-1: Teicoplanin — correct class call, correct self-resistance, correct architecture

**Source:** BGC0000440 live run 2026-07-09

The teicoplanin cluster (MIBiG BGC0000440, *Actinoplanes teichomyceticus*) is the primary calibration case for glycopeptide detection. Expected findings and verified outputs:

| Expected finding | Observed output | Status |
|---|---|---|
| NRPS class call | `Architecture_capacity: glycopeptide; Class_Conf: HIGH` | ✅ CORRECT |
| T43-GPA trigger | `T43-GPA_glycopeptide: 13 hits / 1 BGC` | ✅ CORRECT |
| T43-HAL trigger | `T43-HAL_halogenase: 1 hit / 1 BGC` | ✅ CORRECT |
| VanHAX T1 resistance | `VanHAX_like: 3 hits; T1 BGCs: 1` | ✅ CORRECT |
| Full-contig boundary | `edge_status: Full-contig; corrected: 0.25` | ✅ CORRECT |
| Architecture grade D | `architecture_confidence: D` | ✅ CORRECT |
| KCB self-match | `kcb_cumulative: 58,408; kcb_protein_hits: 53` | ✅ CORRECT (self-hit expected) |
| OVER_MERGE_CANDIDATES | Flagged (2 protoclusters) | ✅ CORRECT (NRPS + PKS + T3PKS) |

The engine correctly identifies the glycopeptide class from domain content alone (architecture-first), independently of the KCB anchor. The three-channel reconciliation principle is demonstrated: NRPS domain architecture → glycopeptide class; T43-GPA trigger (OxyA/B/C + DpgS + HPG enzymes) → class confirmation; VanHAX → T1 self-resistance confirms this is a genuine antibacterial BGC.

**Lead tier: Medium.** This is lower than expected for a benchmark known antibiotic. The reason: Full-contig architecture grade (D) and the AB score of 62.0 falls below the Exceptional (≥85) and High (≥70) thresholds. The single-contig input does not have POOR/VERY_POOR tier mitigation. This is correct behaviour — a single-contig MIBiG reference fragment is not the same evidence quality as an interior cluster in a completed genome.

### CAL-2: BGC0000243 (macrotetrolide) — known false-negative for core-gene count

From the calibration corpus: BGC0000243 encodes macrotetrolide biosynthesis but has 0 antiSMASH-scored core biosynthetic genes. The non-canonical assembly logic is not captured by the standard PKS/NRPS rules.

**Documented behaviour:** this cluster will score as Architecture grade E (weak/ambiguous) and likely land in the Inventory tier. This is a false-negative at the scoring level — a failure of the scoring model's core-gene floor assumption, not a pipeline bug. The standing prevention rule: never automatically downgrade low-core-gene-count BGCs without first checking the calibration corpus.

**Detection path without engine support:** the CCTT T43 trigger table does not have a macrotetrolide-specific trigger. Detection requires per-gene BLASTp followed by literature-lookup of the specific biosynthetic genes (NonS, NanA, NonC, etc.). This is an OFFLINE_EVIDENCE_ALLOWED case where BLASTp is the primary evidence channel.

### CAL-3: BGC0000240 (lomaiviticin) — T2PKS aromatic with diazo warhead

From the calibration corpus: lomaiviticin A contains a diazotetrahydrobenzo[b]fluorene moiety — a diazo (-N=N-) warhead that makes it an extremely potent DNA-cleaving agent. In the CCTT framework, the `T43-NN_n_n_bond` trigger covers diazo.

**Expected behaviour if the cluster is in a real genome:** the `azoxy/diazo/hydrazine` pattern (one of 6 patterns in T43-NN) would fire if annotation tokens include "diazo" or "azoxy." However, many early antiSMASH annotations of this cluster use "PKS enzyme" and similar generic names that do not include the diazo token. In practice, T43-NN may not fire on lomaiviticin without explicit diazo annotation in the GBK.

**Prevention rule:** whenever T2PKS aromatic clusters with high novelty scores appear, manually check whether the annotation includes "diazo," "azoxy," or "diazotetrahydro" tokens. If absent, note that T43-NN could not be detected from annotation alone — this is missingness, not absence.

---

## Group 12: Tools Execution Notes from Live Session

*Real outputs from tools executed against the teicoplanin calibration strain on 2026-07-09. Source: live tool runs.*

### TOOL-1: preflight_zip_hygiene.py — passes cleanly on clean ZIPs

```bash
python3 tools/preflight_zip_hygiene.py tests/fixtures/micromonospora_humida_JAFEUC01.zip
# → OK: micromonospora_humida_JAFEUC01.zip is clean (no cache / unexpected hidden / oversized entries)
```

The tool checks for: macOS resource forks (`._*`, `__MACOSX/`), `.DS_Store` files, nested ZIPs, and files exceeding a size threshold. The teicoplanin fixture passes clean. Any antiSMASH ZIP exported from macOS should be run through this check before pipeline submission.

### TOOL-2: gen_marker_catalog.py --check — confirms no catalog drift

```bash
python3 tools/gen_marker_catalog.py --check
# → marker catalog OK — in sync with source_scans.py (14 tables)
```

The catalog contains 14 tables (CASSETTE_PATTERNS, CCTT_PATTERNS, CCTT_VETOES, CHITINASE_PATTERNS, DOMAIN_CLASS_PATTERNS, FLBR_PATTERNS, MOBILE_ELEMENT_PATTERNS, PRIMARY_METABOLISM_PATTERNS, REGULATOR_PATTERNS, RESISTANCE_PATTERNS, TFBS_MOTIFS, TRANSPORTER_PATTERNS, UMED_PATTERNS, VETO_CONTEXT_PATTERNS). The `--check` mode compares the live pattern tables in `mamey/source_scans.py` against the on-disk `docs/MARKER_CATALOG.generated.md`. Any pattern added to source without regenerating the catalog would produce a FAIL here.

### TOOL-3: sapote_workflow.py — W0-W2 pass, W3-W10 blocked as expected

After extraction only (no Mode B authoring), the workflow gate correctly shows:
- W0 PASS: `manifest.json (191769B); gate_validation.json ok=MAMEY_COMPLETE; checksums_sha256.txt present; bgcs=1`
- W1 PASS: `BGC0000440_4_triage_board.csv (1 BGC rows); scan_states=yes`
- W2 PASS: `BGC0000440_4c_AB_lead_board.csv (1) + BGC0000440_4c_AF_lead_board.csv (1)`
- W3 PENDING: `no mode_b_templates/ — run mamey emit-modeb-template --batch`
- W4–W10 BLOCKED

This is correct and expected. The workflow gate correctly reads actual artifact contents (file sizes, row counts) rather than just file existence. The blocking cascade (W4 blocked by W3, W5–W10 blocked by their predecessors) enforces the mandatory ordering.

### TOOL-4: render-all-figures — all five modules run successfully

```
render-all-figures output:
  smoke          RAN   3 fig(s) → package/smoke_figures
  brief          RAN  14 fig(s) → package/
  locus-maps     RAN   1 fig(s) → package/locus_maps
  figure-suite   RAN   2 fig(s) → package/figures_rendered
  domain-level   RAN   3 fig(s) → package/domain_level/figures
  total figures: 23
  gathered 26 fig(s) → package/figures/
```

The 3-figure gap (reported 23, gathered 26) is normal: the gold_figures directory contains 2 additional F-series figures that the aggregation step picks up. The figure manifest at `figures/FIGURE_INDEX.csv` is the authoritative list.

### TOOL-5: claim_safety_linter.py — 2 findings in auto-generated report

```bash
python3 tools/claim_safety_linter.py BGC0000440_compiled_report.md
# → claim-safety: 2 finding(s)
#   ✗ possible identity overclaim: 'are claim-safe' (use capacity/similarity framing)
#   ✗ possible identity overclaim: 'is pinned' (use capacity/similarity framing)
```

Both findings are false positives: "are claim-safe" is a procedural statement about the report's own content (not a biosynthetic claim), and "is pinned" refers to the bioactivity framework (extract-level activity is pinned to the strain, not a BGC). The linter uses pattern matching and cannot distinguish these procedural uses from genuine overclaims.

**Prevention:** the linter should be run and its findings reviewed, not auto-resolved. False positives in procedural language are common. Genuine overclaims use "produces," "is confirmed," "is [compound name]."

---

*v2 additions: Groups 11–12 (calibration cases, live tool outputs) · Bundle v9.7.241 · 2026-07-09*

---

## Group 13: Fabricated Observations — The PHANTOM_LOCUS Class

*This group documents the most serious class of defect this pipeline can produce: not a wrong number, but a fabricated observation, in the one section whose job is to report observations. Source: `CHANGELOG.md` v9.7.246, `mamey/modeb_structure_gate.py:_phantom_locus_findings`.*

### FAB-1: A real BLASTp result from a different organism, templated into every card

**Severity:** Must-fix (release-blocking) · **Fix in:** v9.7.246 · **Cards affected:** 74 across two strains

**What happened.** `modeb_template_emitter._section_body(4)` — the §4 gene-by-gene authoring template — hardcoded a real per-gene BLASTp result belonging to a different organism:

> *"per-gene BLASTp overturned two of ten on BGC006 (β-lactamase→esterase, phenol-hydroxylase→ferritin)"*
> *"the offline, deterministic channel that settled BGC006 ctg12_71"*

Those numbers are genuine. They live in `Wheelhouse/validations/BGC006_online_blastp.csv`, whose organism is ***Amycolatopsis* sp. NPDC004378**. Templated into §4, they were emitted verbatim into **every card of every strain** — asserting a specific per-gene BLASTp outcome for strains on which **no BLASTp had ever been run**, and citing `ctg12_71`, a locus that exists on neither AS-XXX's BGC006 (NODE_1) nor AS-XXX's (NODE_16).

§8 carried a lesser instance: *"the BGC006/colibrimycin fix: score 3734"* — another strain's BGC id and another run's KCB score.

**Why every guard passed it.** Claim-safety, evidence-presence, citation, and padding gates all cleared those 74 cards, because none of them ever asked the only question that matters about a cited locus: **does this gene exist in this organism?** The claim-safety linter checks phrasing; the citation gate checks that a node·region locator is present somewhere; the evidence-presence gate checks that §4 is non-empty. None validates the *referent*.

**Why it survived review.** The examples were doing real work — they illustrated a correct and important methodology (antiSMASH Pfam calls are hypotheses, not function; BLASTp overturns some of them). **A vivid, true example from the wrong organism is more dangerous than an obviously wrong one, because it survives review.** A reader checks whether the example makes the point. It did. Nobody checked whether the locus belonged to the strain in front of them.

**The fix, in two parts.**

*Source.* §4 keeps the methodology and now cites the validation set **by path**, with the instruction "a different strain — do not cite its loci here." §8 keeps the lesson (*"a high KCB score backed by only a handful of shared genes is NOT the compound"*) as the **colibrimycin-class fix**, without the foreign BGC id or score. All 30 sections swept: zero foreign loci, zero foreign BGC ids, zero foreign scores remain in any emitted body.

*Net.* A new **`PHANTOM_LOCUS` lint (ERROR, release-blocking)** in `mamey/modeb_structure_gate.py:_phantom_locus_findings`:

```python
_LOCUS_RE = re.compile(r"\bctg\d+_\d+\b")

def _phantom_locus_findings(card_md, bgc_context=None):
    known = (bgc_context or {}).get("known_loci")
    if not known:
        return []                       # silent without a CDS table
    known = {str(k).strip().lower() for k in known}
    cited = {m.group(0) for m in _LOCUS_RE.finditer(card_md)}
    phantom = sorted(c for c in cited if c.lower() not in known)
    ...  # ERROR finding, one per card
```

`authored_verify` loads `known_loci` from the sealed `<strain>_cds_table.csv` (globbing `*_cds_table.csv` and `cds_table.csv`). `PHANTOM_LOCUS` is added to `_READINESS_BLOCKING`, alongside `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`, and `FACT_MISMATCH`. A card citing a gene from another organism **cannot reach `RELEASE_READY`** and therefore cannot be presented.

**Verified against the real AS-XXX package:** 758 loci loaded; `ctg12_71` not among them; the exact leaked sentence raises ERROR and drops `readiness_state` below `RELEASE_READY`. A card citing that strain's real loci passes clean.

**Two sibling lints extended this class in v9.7.256** (same file, same entry points), for fabrications `PHANTOM_LOCUS` cannot see because the gene *does* exist:

- **`LOCUS_BGC_MISMATCH`** — a real locus cited under the wrong BGC (the AS-XXX BGC006/BGC010 leak class: templated boilerplate carries a real gene into another BGC's card). `authored_verify` builds per-BGC membership so a gene cited under a BGC it does not belong to raises ERROR.
- **`PANEL_ABSENT_CLAIM`** — a per-gene BLASTp *result* asserted for a BGC that has **no BLASTp panel** in the package. It keys on whether a BGC has a panel *selection*, not on returned alignments — so a fabricated result on an in-panel-but-never-run BGC still passes (reproduced on `S_erythraea` BGC017); the residual gap is "asserted result vs actual alignments," to be closed by extending this lint to require a results artifact, not by a new gate.

Both are ERROR-severity, so they drop the card to `DRAFT` via the any-ERROR path; neither is a member of the four-code `_READINESS_BLOCKING` set.

**Fail-silent by design.** With no CDS table the lint returns `[]` and says nothing. The reasoning is stated in the source: *"it cannot judge what it cannot see, and a false accusation of fabrication is worse than none."* This is the correct direction for a lint whose ERROR verdict is "you fabricated an observation."

**The 74 already-authored cards are not repaired by this cut.** Re-running `verify-modeb` against them with a sealed package will flag every one. **Every §4 and §16 paragraph containing `ctg12_71` should be deleted, not reworded** — there is no BLASTp result to reword.

### Prevention rules derived from FAB-1

1. **A template that contains a concrete observation is a template that will assert that observation about every subject it is applied to.** Templates may carry methodology, instructions, and structure. They may not carry findings. If an example is needed, cite it by path and name the organism, with an explicit "do not cite its loci here."

2. **Every guard should be able to state the question it asks.** The four guards that passed these cards each asked a real question — is the phrasing claim-safe, is the section non-empty, is a locator present, is the prose long enough. None asked "is this referent real." When adding a gate, write down the question it answers, then check whether any existing gate already answers it. If they collectively leave a question unasked, that is the gate to build.

3. **Referent validation is distinct from claim validation.** "Capacity consistent with a glycopeptide" is claim-safe phrasing about a real cluster. "BLASTp settled ctg12_71" is unsafe *not because of its phrasing* but because `ctg12_71` does not exist here. The claim-safety linter cannot catch this class. Only a lint with access to the strain's own CDS table can.

4. **A true example from the wrong organism survives review.** Reviewers check whether an example supports its point. They do not, by default, check whether the example belongs to the subject. Any hardcoded identifier in a template — a locus tag, a BGC id, a score, an accession — is a fabrication waiting for a subject.

---

## Group 14: The "Defined and Never Invoked" Pattern

*Four separate cuts have each fixed one instance of the same shape: a capability is written, tested in isolation, and never wired to the path that would exercise it. The project's own changelog names this pattern explicitly. Documented here as a class because it keeps recurring.*

| Cut | Symptom | The unwired thing |
|---|---|---|
| v9.7.239 | Novelty guard silently fell back to ClusterBlast | Three readers of `blastp_online/<BGC>_online_blastp.csv`; **zero writers** |
| v9.7.242 | Doc-rot path references passed every guard | `check_dangling_refs --strict-paths` existed; nothing ran it |
| v9.7.244 | `tab-reconcile --bgc` reported the wrong region's evidence | `_choose_record()` computed `wanted_region` (line 139) and **never read it**; `_gene_overview_summary()` hardcoded `areas[0]` |
| v9.7.245 | Every caller silently tripled its NCBI submission size | `DEFAULT_BATCH = 10` was added in v9.7.240 and **nothing ever read it**; `chunk_proteins` still defaulted to `MAX_BATCH = 30` |
| v9.7.335→.338 (MB-01) | `verify-modeb` printed a bare `OK` that read as "§4 coverage verified" when it never was | The §4_BLASTP_COVERAGE / `EVIDENCE_GAP` gate could not fail on any card from the supported workflow — its bare-verdict branch matched the emitter's own unauthored skeleton text, and its coverage `%id` clause was satisfied by the digits inside the locus tag (`ctg13_108` supplied the "13"). Holes closed in .335; **the gate now bites** in the §1–§30 authoring path as of v9.7.338 |

**MB-01 detail (v9.7.338 — the §4 gate now bites).** With those two holes closed, `verify-modeb` on a card whose strain carries a BLASTp panel now raises an `EVIDENCE_GAP` / `COVERAGE_UNVERIFIED` **WARN** when §4 asserts `CONFIRM/REFINE/OVERTURN` without the reconciled per-gene closest-match table, or when no authoritative package core count reached the gate (the summary reads `OK (§4 coverage NOT verified — no package core count)`). WARN-level, never a structural refuse; re-run with `--package … --bgc …` so the real-core-count coverage gates. The new `--interp` flag adds a companion WARN-only interpretation/judgment gate (alternative reads, resolving experiment, capacity framing).

**The common shape.** A constant, a flag, a computed local, or a whole output file is created with correct semantics and a passing unit test — and then the production call path bypasses it. Unit tests pass because they exercise the function directly. Integration is never checked, because there is no test that asks *"does the thing that should call this actually call it?"*

**Diagnostic.** For any newly added constant, flag, or file: grep for its name across the tree and count the *read* sites, not the write sites. `DEFAULT_BATCH` had one definition and zero reads. `wanted_region` had one assignment and zero reads. `blastp_online/` had three readers and zero writers.

**Structural fix in the bundle:** `tools/file_atlas.py` (v9.7.243) generates `docs/FILE_ATLAS.csv` / `.md` with per-file fan-in, fan-out, CLI verbs, and test references, and an **`orphan`** column: no importer, no CLI verb, no test naming it. Live count on this bundle: **35 orphan candidates of 280 files**; **57 files no test names at all**; 74,981 total lines. The orphan list is the roll pool for the Bunny Hop audit game — a module nothing imports and nothing tests is the population from which this defect class is drawn.

---

## Group 15: Wrong-Region and Wrong-Field Silent Answers

### REG-1: `tab-reconcile --bgc` reported a different region's evidence

**Severity:** High (silent wrong answer) · **Fix in:** v9.7.244

`_choose_record()` computed `wanted_region` and never read it; `_gene_overview_summary()` then hardcoded `areas[0]` — the first region on the contig. **Reproduced on a real cohort antiSMASH JSON [Redacted — publication in preparation]:** the contig carries three regions. The target BGC is region003. The ledger reported:

```
span=233558-275304; products=NRPS-like; CDS=535
```

That is region001's span, region001's products, and the **whole contig's** CDS count. Any BGC that is not the first region on its contig received another cluster's evidence — and the tab ledger is the artifact a Mode B card cites.

**Fix:** `_region_index()` resolves the region label to the area index (antiSMASH `areas` carry no region number; **index order IS the region number**, verified against the real JSON). `_gene_overview_summary(rec, area_idx)` takes the resolved area. New `_feature_in_span()` scopes the CDS count to the region rather than the contig.

**Verified on the real record, all three regions:** `region001 → 233558-275304 / NRPS-like / 40 CDS` · `region002 → 332841-394488 / NRPS / 48` · `region003 → 438609-463791 / lanthipeptide-class-i / 22`. The 22 is an independent cross-check: the BGC018 BLASTp panel run in v9.7.239 had exactly 22 queries.

**Why no test caught it:** the reference fixture (BGC028/AS-XXX) sits on a contig with exactly **one** region, where `areas[0]` is always right. **A single-region fixture cannot exercise region selection.** This is the fixture-shape lesson: a test fixture that cannot distinguish the correct behaviour from the bug is not a test of that behaviour.

### REG-2: `region_label(-1)` returned `region001`

**Severity:** Medium · **Fix in:** v9.7.245

`re.search(r"(\d+)", "-1")` matches `"1"` — the sign is not part of `\d+` — so the negative was silently dropped **before** the `n > 0` check could see it. The function contradicted its own stated rule ("anything ≤ 0 is region_unknown"). Now a leading minus is rejected before the digits are read: `-1`, `-7`, `"-1"`, `" -12 "` → `region_unknown`.

Unreachable from antiSMASH input, real against the design. **Found by an outside verifier who tested the boundary the fix note named, instead of assuming the note covered it.** That is the correct verification posture: a fix note that says "anything ≤ 0 is rejected" is a claim to be tested, not a claim to be believed.

### REG-3: `assembly_locator` answered from a different field when the value was `0`

**Severity:** Medium · **Fix in:** v9.7.244

`get("region_number") or get("Region")` — Python's `or` treats `0` as absent, so a region number of `0` silently fell through to a **different field**. Now an explicit `None` / `""` check.

**Class:** the `x or y` fallback idiom is unsafe whenever `x` can legitimately be `0`, `""`, `[]`, or `False`. Use `x if x is not None else y`.

### REG-4: `region_label("region003")` raised ValueError

**Severity:** Medium (latent) · **Fix in:** v9.7.244

Callers read `antismash_region`, whose value **is** the string `"region003"`. The crash was latent only because every current caller happened to pass an int. `crosswalk.py` has **fan-in 11** — the highest-risk latent crash in the bundle. Now tolerant: digits extracted; anything without digits returns `region_unknown`.

### REG-5: `bgc_guide._load_blastp_store()` skipped every overlay row

**Severity:** High · **Fix in:** v9.7.245

`ingest-blastp --package` writes `blastp_online/<BGC>_online_blastp.csv`, whose gene column is `locus_tag`. `_load_blastp_store()` did `if "query_gene" not in r: continue` — **skipping every row of the overlay.** The BGC Guide could not see the nr evidence that v9.7.239 was written to create and v9.7.241 was written to stop truncating.

**Confirmed on the real overlay column set: 0 rows loaded before, 1 after.** Now accepts either column, `query_gene` winning a tie.

**Class:** a column-name mismatch between a writer and a reader is invisible to both. The writer's tests check that the file is written correctly; the reader's tests use a fixture with the reader's expected column. Neither test reads the other's artifact. **The receipt is the on-disk file, read by the actual consumer.**

---

## Group 16: Atomic Write and Permission Defects (`tools/_wbio.py`)

*`tools/_wbio.py` is the highest-fan-in file in the bundle: **38 importers**, 125 lines, and — before v9.7.243 — **1 test**. Three defects, all reproduced before the fix.*

### WBIO-1: Permission widening on every atomic rewrite

**Severity:** High (in a bundle that ships a MERGED-PRIVATE tier) · **Fix in:** v9.7.243

`os.replace()` adopts the **temp file's** mode. Rewriting a `0600` deliverable therefore left it **`0644`** — world-readable. All four helpers (`atomic_save`, `atomic_write_text`, `atomic_dump_json`, `atomic_open`) now inherit the target's mode via `_inherit_mode(path, tmp)`.

### WBIO-2: Stray `.tmp` files left on failure

**Severity:** Medium · **Fix in:** v9.7.243

`atomic_dump_json` on a non-serializable object left `x.json.tmp` on disk. `atomic_save` and `atomic_write_text` leaked the same way. Only `atomic_open` cleaned up. All four now `_discard(tmp)` and re-raise.

### WBIO-3: The `.bak` window inverted the module's own invariant

**Severity:** High · **Fix in:** v9.7.243

`atomic_save(keep_bak=True)` did `os.replace(path, path + ".bak")` **before** moving the temp in — creating a window in which the target file **did not exist at all**. That is the exact opposite of this module's stated invariant (the target is always present and always complete). `.bak` is now a `shutil.copy2` rather than a rename.

**Test coverage: 1 → 6.**

---

## Group 17: Documentation Anchors That Drift Silently

### DOC-1: The monolith's version anchor was 185 cuts behind

**Severity:** Medium · **Fix in:** v9.7.243 (`tools/check_monolith_freshness.py`, new, WIRED)

`docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` is the parent design controller — referenced by **20 files**, including `prompts/CLAUDE_SYSTEM_PROMPT.md` and at least one test. Its convention (reviewed at checkpoints, not bumped per patch) is sound. Its **anchor** was not: at v9.7.242 it still read

```
"vetted against bundle v9.7.6 (last full read-through 2026-06-13)"
"current bundle 9.7.57 / engine 1.9.64"
```

**185 cuts of drift, with no signal.** A fresh chat reads the monolith first.

**The gate does not demand a re-read.** It demands that the monolith state, truthfully, how far behind it is. Four checks:
1. The monolith exists and names a `vetted against` bundle version
2. The `current bundle X / engine Y` parenthetical, if present, matches live `pyproject.toml` / `BUILD_STAMP`
3. The drift (live patch − vetted patch) is reported, and fails above `--max-drift`
4. **No retired doctrine is present:** assembly tiers 66/50/33, per-BGC BSL-2 flagging, AS_SCRUB, the PUBLIC/PRIVATE figure divider

**The doctrine scan came back clean** — the monolith's *content* was current even where its *label* was not. The lying `current bundle X / engine Y` parenthetical was deleted; `pyproject.toml` is authoritative. The anchor now records a **spot-vet** (doctrine + anchor + dangling refs) as such, rather than pretending to be a read-through.

**Live receipt on this bundle:**
```
monolith: vetted v9.7.242 | live v9.7.246 | drift 4 patches | 450,214 chars
check_monolith_freshness: PASS (anchor honest, no retired doctrine)
```

**The gate false-positived on its own first run,** flagging a freshly written "no per-BGC BSL-2 flagging" as an assertion of the doctrine it denies. A negation-aware window was added — the same lesson the v9.7.233 novelty lint learned. Verified it still fails on a genuine assertion (`GOOD >= 66%`).

**Class:** a documentation anchor that restates a version is a claim, and claims rot. Either derive it from the single source of truth at read time, or gate it.

---

## Group 18: The Version-Lineage Split (v9.7.244, two of them)

**Status:** Open — a project decision, not a technical fix.

Two active codebases have each shipped a `v9.7.244`. The other lineage's P8 / P9 / P10 findings predate this cut. As of v9.7.245, **P8 and P10 exist in this lineage by independent reproduction and fix, not by merge** — the code differs from theirs even where the behaviour now agrees. P9 (`background_tier` in `genome_explore`) is **not merged**: it does not exist in this lineage, and guessing its name or semantics would produce a third incompatible implementation.

Two further parallel `.243` cuts exist: a Bunny Hop audit lineage (`file_atlas`, `_wbio` hardening, `kcb-frontpage` fail-closed, monolith gate) and a documentation/exit-code lineage (`P-emit-01` exit-3 on empty `--scope leads`, `--fail-on-empty` flag, `docs/user_guides/` advanced to v2/v3). Neither contains the other.

**Recommended resolution (offered, not taken — this is a PI decision):**

1. Freeze both lineages at their current heads (`v9.7.246-bunnyhop` here, `v9.7.244-guide` there, plus the `v9.7.243-docs` cut).
2. Consolidate at **`v9.7.250`** — a number no lineage has used, with room beneath it.
3. Apply in sequence: this lineage's `.243`–`.246` (file atlas, `_wbio` hardening, `kcb-frontpage` fail-closed, `tab-reconcile` region resolution, crosswalk hardening, monolith gate, PHANTOM_LOCUS lint), then the docs lineage's `P-emit-01` + `docs/user_guides/` v2/v3 + `math_reference_vol2.md`, then the other lineage's P8/P9/P10 diffs, resolving P8/P10 against the versions here.
4. Whoever consolidates must run the full suite on the merged tree.

**On test counts across lineages:** `2884p / 152s` here vs `2877p / 147s` there vs `2857p / 152s` on the docs lineage is **expected** — different trees with different tests. **Zero failures on all three is the invariant that matters.** Chasing the counts to equality would mean one of them was lying.

**On the six independent `mamey run` results:** 46 raw / 32.25 corrected / MODERATE, six times, across lineages. That is the scoring parity claim doing its job — the engine is 1.9.111 everywhere, and it produces identical numbers everywhere.

---

## Group 19: Standing Rules Read From the Registry, Not Hardcoded (v9.7.338)

### RG-01: the NAPAA standing rule now follows the registry

**Severity:** Medium (a rule diverged from its single source of truth) · **Fix in:** v9.7.338

**The shape.** `mamey/data/rules_registry.json` is the single source of truth for standing rules (permanent exclusions/downgrades and their `false_positive_guard` contexts). A hardcoded NAPAA exclusion had drifted from that registry: it could **auto-exclude a BGC whose own product is NAPAA** (ε-poly-L-lysine synthetase / TIGR02353) from comparative/ecological claims, even though the registry classifies NAPAA as **NEUTRAL** — "common and frequently adjacent to genuine BGCs; neither downgraded nor excluded" (`genus_reference.py` had already noted this drift: its `{saccharide, fatty_acid, NAPAA, hgle-ks}` set "excluded NAPAA (now registry-neutral)").

**The fix.** The NAPAA rule is now read from `rules_registry.json` (registry id `NAPAA`), so own-product NAPAA is no longer auto-excluded — it stays lead-eligible and available to comparative/ecological claims. The retired Nosema hypothesis does not justify excluding NAPAA itself. Combo-detection routing that keys on TIGR02353 is unchanged; saccharide / primary-metabolism / enediyne-gate / bryo-HGT rules are unchanged.

**Class:** the same drift lesson as Group 17 — a rule restated in code away from its registry is a claim, and claims rot. Derive standing-rule behaviour from `rules_registry.json` at evaluation time (`scoring.py::standing_rule_for`), never from a parallel hardcoded copy.

---

*v3 additions: Groups 13–18 (PHANTOM_LOCUS fabrication class, defined-and-never-invoked pattern, wrong-region silent answers, atomic-write defects, doc anchor drift, version-lineage split) · Bundle v9.7.246 · 2026-07-09*
*v9.7.338 additions: Group 14 extended with MB-01 (the §4 Mode-B evidence gate now bites) + Group 19 (RG-01, NAPAA standing rule now follows the registry) · Bundle v9.7.338*
