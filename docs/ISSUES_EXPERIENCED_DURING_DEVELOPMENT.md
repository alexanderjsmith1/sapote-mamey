# Issues Experienced During Sapote–Mamey Development

*A living record of significant bugs, misidentifications, and design failures encountered during the build arc — with root causes and how each was resolved. Maintained for developer orientation, audit continuity, and as a reference for anyone extending the pipeline.*

*Current arc: v9.7.102 → v9.7.148c · Engine 1.9.98 → 1.9.100 · 2026-06-22 – 2026-06-29*

---

## How to read this document

Each entry has: what went wrong, what triggered its discovery, the root cause, and the fix. Severity follows the patch chat convention: **Must-fix** (blocks release), **High** (degrades science or breaks a user-facing workflow), **Medium** (correctness issue with workaround), **Low** (doc gap, cosmetic, or latent).

Entries are roughly reverse-chronological within themes.

---

## 1 · PDF Compilation Issues

### 1.1 — Overlapping text on the first section page of a compiled report
**Severity:** High · **Discovered:** v9.7.148c · **Trigger:** AS-XXX Full Report visual inspection

**What happened:** The first section page (Synopsis) of the AS-XXX compiled PDF showed giant overlapping text — three layers of header information stacked on the same vertical space, making the page unreadable.

**Root cause:** The testing chat was placing a mini-header block at the start of each section body, e.g.:
```
AS-XXX Analysis Synopsis · Saccharopolyspora sp. AS-XXX · Apis mellifera honeybee...
Bundle: Sapote–Mamey v9.7.146 · Engine 1.9.100...
```
This is correct on the cover page. But in subsequent sections, the LaTeX renderer already places a running header automatically at the top of every page (strain name · PRIVATE). Adding the mini-header as body text produces three simultaneous layers: the YAML `\maketitle` block, the automatic running header, and the body text header. All three land on the same vertical position.

**Fix:** Execution slice §13 now specifies explicitly: section bodies begin directly with the section heading (`# 1. Synopsis`) — no repeat of strain/date/bundle metadata, no mini-headers. The running header is placed by the renderer automatically and must not be duplicated in the Markdown body.

**Prevention:** Do not copy the cover page header block into any subsequent section. If a section needs a provenance reminder, put it in a footnote, not a heading.

---

### 1.2 — Dark blue background / illegible text in compiled PDF
**Severity:** High · **Discovered:** v9.7.148 review · **Trigger:** AS-XXX Mode B PDF upload

**What happened:** The AS-XXX PDF had black text against a dark blue background, making it nearly unreadable. This is visually inverted from the intended white-background black-text format.

**Root cause:** The testing chat used `wkhtmltopdf` directly to render HTML to PDF. `wkhtmltopdf` inherits dark-mode CSS from the system environment, so if the host machine has dark mode enabled, the generated PDF adopts dark backgrounds. The pipeline's own PDF tool (`tools/md_to_pdf.sh` → pandoc → xelatex) produces clean white-background output and was not used.

**Fix:** Execution slice §13 explicitly bans `wkhtmltopdf` for compiled report rendering. The required path is: produce Markdown first (`<strain>_Analysis_Report_<date>.md`), then render via `tools/md_to_pdf.sh`. The Markdown file is the canonical deliverable; the PDF is a presentation copy.

---

### 1.3 — Compiled report was Mode B cards only, not a complete deliverable
**Severity:** High · **Discovered:** v9.7.148 review · **Trigger:** AS-XXX Mode B PDF

**What happened:** The testing chat produced a 7-page PDF titled "Mode B Report" and treated it as the compiled analysis deliverable. It contained Mode B cards only — no layperson guide, no figures, no ecology section, no fermentation guidance, no wet-lab matrix, no triage board, no BLASTP evidence table.

**Root cause:** The execution slice §13 specification (added in v9.7.148) described a 10-section compiled report but did not specify a build order or make clear that the Mode B cards are one section among many, not the entire document. The testing chat interpreted "compiled report" as "all my Mode B cards in a single file."

**Fix:** Execution slice §13 was expanded to 14 required sections with an explicit build order:
- Step 1: Generate derivable figures from existing CSVs (BGC ranking, class composition, assembly completeness)
- Step 2: Generate domain-strip locus maps for top-priority BGCs from GBK data
- Step 3: Resolve any wrong or pending cards (reclassifications, invalidations)
- Step 4: Assemble in section order — Cover → Executive summary → Layperson guide → Assembly summary → Triage board → Figures → Ecological synthesis → Priority lead deep-dives → Complete Mode B cards → §21–§30 extensions → BLASTP evidence table → Fermentation guidance → Wet-lab matrix → Outstanding actions → Methods

Target length for a 13-BGC strain with 10 cards: 40–80 pages.


### 1.4 — Blank pages from double section breaks
**Severity:** Medium · **Discovered:** v9.7.148c review · **Trigger:** AS-XXX PDF visual inspection

**What happened:** The 111-page AS-XXX compiled report had 16 near-blank pages — 8 completely blank pages and 8 pages containing only a section header (e.g. "Section 3 — Chapter — BGC Landscape") with no content. These appeared at every major section boundary.

**Root cause:** The Markdown source used a pattern that generates two forced page breaks per section transition: a `---` rule before a dedicated section title block, then another `---` rule before the actual section heading. LaTeX renders each `---` as a `\clearpage`, producing two blank-ish pages before content resumes. In a 111-page document this wasted ~14% of pages.

**Fix:** Execution slice §13 now specifies the correct single-break pattern:
```
[last content line]

---

# 3. Chapter — BGC Landscape

[first content line]
```
No dedicated section title pages. No double rules. No `\clearpage` or `
ewpage` commands.

---

### 1.5 — 324 bare BGC ID instances in compiled PDF prose
**Severity:** High · **Discovered:** v9.7.148c review · **Trigger:** AS-XXX PDF audit

**What happened:** An audit of the AS-XXX compiled report (111 pages) found 324 bare BGC ID instances — `BGC028`, `BGC020` etc. — in prose sections without node/region citation. This included exclusion tables, lead tier tables, cross-references throughout the Mode B cards, fermentation guidance, and the ecological synthesis. The §15 rule (added in v9.7.148b) was not in effect when this report was generated (it ran on v9.7.146).

**The scale of the problem:** 383 total bare BGC instances across the document. Of those, 28 were in the TOC (structurally acceptable — TOC entries reference IDs by design), 4 on the cover summary table (short form acceptable), and 324 in prose (all violations).

**Root cause:** §15 was added to the execution slice in v9.7.148b after this report was produced. Additionally, even with §15, a compiled report requires a dedicated pre-submission scan specifically for bare BGC patterns — this is non-trivial at 100+ pages.

**Fix added to §13:** Before rendering the PDF, run the §15 pre-delivery scan across the entire compiled Markdown source. Budget time for fixing every bare BGC instance — exclusion lists, lead tables, fermentation sections, and ecological synthesis all need individual attention. The cover summary and TOC are the only acceptable exceptions.


### 1.6 — "PI clearance required" persisting in compiled PDF footers and headers
**Severity:** Medium · **Discovered:** v9.7.148c PDF review · **Trigger:** AS-XXX compiled report

**What happened:** The AS-XXX compiled PDF (generated from v9.7.146 analysis) showed "PI clearance required" in the running footer on every page, in the cover page footer, and in the Synopsis section header. The bundle fix (replacing all "PI clearance required" → "PRIVATE") landed in v9.7.148c but the testing chat generated its report Markdown before that cut.

**Root cause:** The "PI clearance required" string was in the report's YAML front-matter (used for the running footer) and repeated as body text in the Synopsis classification line. Bundle fixes to source files don't retroactively change already-generated Markdown reports.

**Fix going forward:** The execution slice §13 now explicitly states that "PI clearance required" must not appear anywhere in the compiled report. Check every footer, every header, every classification line. The correct phrase everywhere is just **PRIVATE**.

---

### 1.7 — Overclaims in layperson guide plain-English descriptions
**Severity:** Medium · **Discovered:** v9.7.148c PDF review · **Trigger:** AS-XXX compiled report

**What happened:** The layperson guide in the AS-XXX report contained several identity overclaims in plain-English prose:
- "AS-XXX produces a structurally distinct analogue" (of totopotensamide) — compound identity claim
- "Our bacterium produces a compound whose..." — implies compound is known
- "The compound is secreted into the growth medium" — implies compound identity
- "The compound is also heavily methylated" — describes an unconfirmed specific product

**Why it happens:** The layperson guide deliberately uses plain English to be accessible. Plain English is inherently more declarative than claim-safe scientific language. Writers naturally slip from "has genes for making X-type molecules" (capacity, correct) to "produces X" (identity, wrong).

**The distinction that matters:**
- ✅ Class-level: "produces siderophore-type iron-grabbing molecules" 
- ✅ Analogy to known: "has genes for making polyketide antibiotics, a class that includes erythromycin"
- ❌ Compound identity: "produces totopotensamide" or "produces a structurally distinct analogue of X"
- ❌ Implied isolation: "the compound is secreted" (implies we know what the compound is)

**Fix:** Execution slice §13 now includes explicit layperson claim-safety rules with ✅/❌ examples. The layperson guide can use "produces" with compound classes but never with compound names or specific structural descriptions.


### 1.8 — Hand-written TOC page numbers up to 53 pages wrong
**Severity:** High · **Discovered:** v9.7.148d review · **Trigger:** AS-XXX compiled PDF

**What happened:** The TOC in the AS-XXX compiled report (115 pages) had page numbers that drifted progressively further from reality as the document grew. The Figures section was listed as page 17 but actually started on page 26 (+9). The Outstanding Work section was listed as page 60 but actually started on page 113 (+53). A user following the TOC would never find the figures.

**Root cause:** The testing chat hand-wrote the TOC with estimated page numbers before finalising the content. As each section grew during composition, the page offsets accumulated. By the end of the document the drift was 53 pages.

**Fix:** Use pandoc's automatic TOC generation via YAML front-matter:
```yaml
---
toc: true
toc-depth: 2
---
```
This inserts `	ableofcontents` at the LaTeX level, computed correctly after two-pass compilation. Do NOT write a manual TOC block in the Markdown body. If no LaTeX renderer is available, omit the TOC entirely — a missing TOC is better than a wrong one.

**Note on figures:** Because the TOC said "Figures ... page 17" but they started on page 26, a user scanning the PDF saw what appeared to be no figure section. The figures were present and correct (9 figures, 20 embedded images, pages 26–33) — just unreachable via the stale TOC.

---

## 2 · BGC Class Misidentification

### 2.1 — BGC044 (AS-XXX, NODE_73): ranthipeptide → mycofactocin
**Severity:** High · **Discovered:** v9.7.146 Mamey run · **Trigger:** TIGRFAM scan of AS-XXX package

**What happened:** BGC044 (NODE_73_length_34773_cov_57 · region001) in AS-XXX was identified as a ranthipeptide BGC across multiple prior analysis sessions. Full §1–§20 Mode B cards and §21–§30 extensions were produced under this assumption. All were wrong. BGC044 produces mycofactocin — a redox cofactor RiPP used in electron transfer, not an antibiotic.

**Root cause:** The analysis was done from raw antiSMASH GBK files before running the Mamey TIGRFAM scan. TIGR03997 (MftE, HMHP hydrolase — a mycofactocin-specific enzyme) was annotated in the raw GBK under a name that looked like an RRE domain used in ranthipeptides. Without the Mamey package's full TIGRFAM sweep, the false class assignment went undetected.

Seven diagnostic mycofactocin markers were present on the contig:
- ctg73_18 (34aa): TIGR03969 = MftA (precursor peptide)
- ctg73_17 (201aa): TIGR03968 = MftB (RRE cognate to MftC)
- ctg73_19 (97aa): TIGR03967 = MftC (radical SAM maturase)
- ctg73_22 (625aa): TIGR03996 = MftD (FMN-dependent oxidoreductase — DIAGNOSTIC)
- ctg73_23 (647aa): TIGR03997 = MftE (HMHP hydrolase — DIAGNOSTIC)
- ctg73_29 (447aa): TIGR03965 = MftF glycosyltransferase
- ctg73_30 (219aa): TIGR03964 = MftF/creatininase

TIGR04085 (SPASM domain) was also present on ctg73_21. SPASM occurs in both ranthipeptide and mycofactocin pathways — its presence alone is not diagnostic for ranthipeptide. The MftD+MftE co-occurrence is definitive for mycofactocin.

**Fix:** Execution slice §14 (PATCH-MYCO-DISAMBIGUATION): when TIGR03967 + TIGR03996 + TIGR03997 co-occur on a contig, the class is mycofactocin regardless of TIGR04085 presence. All prior BGC044 cards for AS-XXX are invalidated. BGC044 is excluded from antibacterial/antifungal leads; reclassified as cofactor biosynthesis.

**Broader lesson:** Mamey-first is a hard gate. Working from raw GBK files before the Mamey package is sealed causes systematic errors that compound through all downstream analysis.

---

### 2.2 — BGC022 (AS-XXX): Linocin_M18 bacteriocin → encapsulin nanocompartment
**Severity:** Medium · **Discovered:** BLASTP validation · **Trigger:** AS-XXX analysis session

**What happened:** BGC022 in AS-XXX was initially assigned as a Linocin_M18 bacteriocin based on antiSMASH domain annotation. BLASTP of ctg4_82 (94.2% identity to *Pseudonocardia sulfidoxydans* family-1 encapsulin shell protein) revealed it is an encapsulin nanocompartment with hemerythrin cargo.

**Root cause:** The Linocin_M18 Pfam domain is structurally homologous to encapsulin shell proteins — antiSMASH's domain model correctly identifies the fold but does not distinguish the biological context. A bare class assignment from antiSMASH annotation without BLASTP confirmation accepted the domain-level call as the class call.

**Fix:** BLASTP validation is required before finalising any class call where the KCB anchor is ambiguous or the antiSMASH class label is unusual. Encapsulins are ecologically interesting (reactive oxygen species management, potential direct antimicrobial activity); the reclassification elevated rather than downgraded this BGC.

---

### 2.3 — BGC036 (AS-XXX, NODE_59): terpene/carotenoid → SUF operon (primary metabolism)
**Severity:** Medium · **Discovered:** v9.7.146 Mamey run

**What happened:** BGC036 was reported by antiSMASH as a terpene/carotenoid BGC. The Mamey v9.7.146 TIGRFAM scan identified the genes as SUFBD (TIGR01980/01981), ABC transporter (TIGR01978), aminotransferase (TIGR01979), and NifU (TIGR01994) — the complete iron-sulphur cluster assembly pathway (sufBCDSU). This is primary metabolism, not a secondary metabolite BGC.

**Fix:** BGC036 dropped from all secondary metabolite analysis. The `primary metabolism` designation via TIGRFAM scanning is authoritative over antiSMASH class calls.

---

## 3 · Test Infrastructure

### 3.1 — Dummy SHA256 checksums in test fixture
**Severity:** Medium · **Discovered:** v9.7.148a audit (F001) · **Trigger:** pytest failure on `test_citation_compact_validate_v97136.py`

**What happened:** `_write_minimal_package()` in the test fixture wrote `"dummy"` as the SHA256 value for every file. The real checksum verification gate was added to `mamey/validate.py` in v9.7.145b. The fixture was never updated. From v9.7.145b onward, the test correctly failed with checksum mismatch errors on its own synthetic package — but this was a test rot failure, not a production issue.

**Root cause:** The checksum gate was added to production code without updating the test fixtures that generate synthetic packages.

**Fix:** `_write_minimal_package()` now computes real SHA256 hashes using `hashlib.sha256(path.read_bytes()).hexdigest()` and writes them into both `manifest.json` and `checksums_sha256.txt`.

**Lesson:** When adding a new validation gate to production code, audit all test fixtures that generate synthetic packages — they must be updated simultaneously or they will fail the gate they're supposed to test.

---

### 3.2 — Missing f-string prefix causing literal output
**Severity:** Must-fix · **Discovered:** v9.7.148a audit (A003) · **Trigger:** hostile audit code review

**What happened:** In `mamey/cli.py`, the multi-strain gold figure skip message was:
```python
print("  Gold domain figures: SKIPPED — only 1 of {len(results)} strains is gold mode")
```
The `f` prefix was missing. Users saw the literal string `{len(results)}` instead of the actual count. The bug was in an `elif` branch that only fires when exactly one of N strains has a gold-mode package — an edge case with no automated test coverage.

**Fix:** `f"..."` prefix added. A test was added to the backlog to catch f-string bugs in the multi-strain branch.

---

### 3.3 — Gene-mention regex matched wrong patterns (false SHALLOW grading)
**Severity:** High · **Discovered:** v9.7.111 · **Trigger:** real genome validation on 5 strains

**What happened:** `mode_b_quality_gate`'s `_RE_LOCUS` regex used `\d{4,6}` to detect locus tag gene mentions. Real antiSMASH locus tags are `ctgN_M` format where M is typically 1–3 digits. The regex matched 0% of real locus tags, causing genuine deep Mode B cards to grade SHALLOW on every strain tested.

**Fix:** `_RE_LOCUS` rewritten to match the structural `ctgN_M` format (any suffix width) plus optional RiPP-precursor class suffixes. Validated at 100% match / 0 false-positive across 5 genomes / 3,916 locus tags.

---

## 4 · Version Synchronisation

### 4.1 — sync_version.py regex breaks on letter-suffix versions (9.7.148a, 9.7.148b...)
**Severity:** High · **Discovered:** v9.7.148b · **Trigger:** post-cut sync_version --check failure

**What happened:** `tools/sync_version.py` uses `re.compile(r'\d+(?:\.\d+)*')` to match version strings in all tracked files. This pattern matches only digits and dots. When the bundle version is `9.7.148a`, the pattern matches `9.7.148` (the digit part) inside `9.7.148a`, then the replacement appends the suffix `a` — producing `9.7.148aa`. On the next run: `9.7.148aaa`. The corruption accumulates with every sync run.

This affected every file that sync_version patches: TAG, SESSION_START_MANIFEST.md, RELEASE_MANIFEST.md, PLAYBOOK.md, prompts, and the CHATGPT_START_HERE.md bootstrap files. The PLAYBOOK.md had two rules with a different syntax (`[\d._]+`) that also did not match letters, causing a separate loop.

**Root cause:** The regex was written assuming semver (digits and dots only). Letter suffixes were introduced later for patch sub-versions.

**Fix (v9.7.148b):** All 44 `re.compile()` version patterns updated from `\d+(?:\.\d+)*` to `\d+(?:\.\d+)*[a-z]*`. The two PLAYBOOK-specific patterns updated from `[\d._]+` to `[\d._]+[a-z]*`. The `[a-z]*` (greedy — zero or more letters) consumes the entire suffix in one match rather than only one character. Two tests added: `test_sync_version_handles_letter_suffixes` and `test_sync_version_check_passes`.

**Lesson:** If your versioning scheme can produce letter suffixes, test sync_version against them before release. The fix is one character per pattern (`*` not `?`), but the corruption it prevents is significant — every affected file needs manual repair.

---

### 4.2 — Stale version strings in RELEASE_MANIFEST.md
**Severity:** Medium · **Discovered:** v9.7.148c audit · **Trigger:** hostile audit of v9.7.148b

**What happened:** `RELEASE_MANIFEST.md` still contained `v9.7.144` as the "Authoritative bundle version", referenced build stamp `20260629v97148a`, and carried the "Quality-recheck fixes" block from the v9.7.144 candidate cycle. All were stale by 4+ minor versions.

**Root cause:** The RELEASE_MANIFEST was partially patched during the v9.7.144 → v9.7.148 arc but the authoritative version line and the quality-recheck block were in sections that sync_version's pattern list did not cover.

**Fix (v9.7.148c):** Three targeted replacements: authoritative version → `9.7.148b`; build stamp → `20260629v97148c`; quality-recheck block replaced with the v9.7.148b patch summary. The `v9.7.144c` reference in Known Limits removed.

---

## 5 · BGC Node/Contig Citation

### 5.1 — Bare BGC IDs in analysis deliverables (no node/contig)
**Severity:** High · **Discovered:** v9.7.148b · **Trigger:** AS-XXX full analysis report audit

**What happened:** An audit of the AS-XXX full analysis report found 79 lines with bare BGC IDs — `BGC007`, `BGC027`, etc. — in prose sections, §28/§30 evidence ledgers, exclusion lists, cross-reference sentences, and the ecological synthesis. The node and region (`NODE_1_length_406707_cov_83 · region001`) were cited correctly in the triage board table but dropped in all subsequent prose.

**Impact:** BGC IDs are Mamey-internal bookkeeping. A collaborator, reviewer, or user returning to the report cannot locate `BGC007` in the assembly or antiSMASH HTML without the node and region. The node citation is the locus identifier; the BGC number is a convenience alias.

**Root cause:** The "BGCs must have the node or contig listed" rule existed in user preferences and CLAUDE_START_HERE.md as a soft guideline. The execution slice had no mechanical enforcement — it specified the format for §1 card headers and minimum candidate cards but not for prose sections, cross-references, or ecological synthesis text.

**Fix (v9.7.148b):**
- Execution slice §15: hard enforcement rule with required format at every citation context, explicit before/after violation examples, and a mandatory pre-delivery scan instruction
- CLAUDE_START_HERE.md: soft guideline replaced with hard rule
- `node_citation_map.json` added as a W7 output in every Mamey package: pre-built `{"BGC007": "NODE_1_length_406707 region001", ...}` lookup

**Required format:**
- First mention in a section: `BGC007 (NODE_1_length_406707_cov_83 · region001)`
- Subsequent mentions within same section: `BGC007 (NODE_1 · r001)`
- Exclusion lists: `NAPAA (BGC023 · NODE_4 · r001)` — not `NAPAA (BGC023)`
- Cross-references: `BGC007 (NODE_1 · r001) and BGC027 (NODE_6 · r001)` — not `BGC007 and BGC027`

---

## 6 · BLASTP and Sequence Issues

### 6.1 — bgc_blastp_panel produces cohort-wide pools, not per-BGC batches
**Severity:** Medium · **Discovered:** v9.7.147 · **Trigger:** user observation that BLASTP batches required manual requests

**What happened:** The `bgc_blastp_panel` runs automatically on every `mamey run` and writes FASTA files into `bgc_blastp_panel/` — but these are cohort-wide pools (20 proteins per file, all BGCs mixed), not per-BGC batches. Mode B cards listed BLASTP priority proteins in prose but did not produce the FASTA files users need to submit. Users had to make a separate explicit request to get per-BGC FASTA batches.

**Fix (v9.7.148):** New `mamey/modeb_blastp.py` module and `mamey modeb-blastp` CLI command. Reads the panel manifest, deduplicates by locus_tag, loads sequences from curated FASTA files, feeds to `BlastpBatchEmitter(batch_size=3)`, writes per-BGC batches to `<pkg>/modeb_blastp/<BGC_ID>/`. Execution slice §12: §16 completion triggers `mamey modeb-blastp`; FASTA emission is required, not optional.

---

### 6.2 — ctg94_18 (AS-XXX, BGC050) at 3,049 aa may exceed NCBI web BLASTP limit
**Severity:** Low · **Discovered:** v9.7.147 analysis

**What happened:** ctg94_18, the Hybrid-KS protein in BGC050 (NODE_94), is 3,049 amino acids — well above the NCBI web BLASTP practical size limit (~100,000 residues per submission, but individual proteins above ~2,500 aa are often rejected).

**Mitigation in execution slice §12:** If NCBI rejects the full sequence for size, split at domain boundaries into ~1,000 aa parts and submit as batches 10a, 10b, 10c. The domain boundaries for a 3-module PKS are approximately at residues 1–1,000 (loading module), 1,001–2,000 (first extension module), 2,001–end (second extension module).

---

## 7 · Figure Generation

### 7.1 — Figures were not produced automatically in smoke mode
**Severity:** High · **Discovered:** v9.7.148 · **Trigger:** AS-XXX testing chat delivering `NO_FIGURES_RENDERED.md`

**What happened:** The testing chat ran with `--chatgpt-safe` (which sets `--brief none`), which explicitly skips all figure rendering. The package contained `NO_FIGURES_RENDERED.md` explaining the skip, but the post-MAMEY_COMPLETE handback did not detect this file and trigger `render-figures` before presenting outputs. Users received a package with no figures.

**Fix (v9.7.148):** RC1 fix in execution slice §3: if `NO_FIGURES_RENDERED.md` is present in the package, run `python -m mamey render-figures --package <pkg>` before presenting the handback. The session is not complete until figure rendering is attempted.

---

### 7.2 — Gold figure suite (F01–F15) existed but never fired automatically
**Severity:** Medium · **Discovered:** v9.7.148 · **Trigger:** user observation ("had to engage to get figures")

**What happened:** `cohort_figures.py` (which IS `make_figures_v3.py`, brought into the engine) implements the full F01–F15 domain heatmap and PCA figure suite. Single-strain gold runs never called `figs_single()`. Multi-strain runs called `cohort_figures_bridge` (RGGMCI-focused figures) but not `cohort_figures.generate()` (the F-series). Users had to request figures explicitly every time.

**Fix (v9.7.148):** Two non-blocking triggers added to `mamey/cli.py`:
- Single-strain gold: after `build_deep_data_files()`, calls `cohort_figures.generate()` → `<pkg>/gold_figures/`
- Multi-strain: when ≥2 packages have `deep_data.json`, calls `cohort_figures.generate()` → `<outdir>/cohort_figures_gold/`

Smoke/standard runs write `GOLD_FIGURES_REQUIRE_GOLD_MODE.md` instead of failing silently.

---

## 8 · Compilation and Packaging

### 8.1 — Package checksum gate failures across multiple cuts
**Severity:** Must-fix · **Discovered:** v9.7.145a–c · **Trigger:** repeated audit F1/F2/F3 findings

**What happened:** Three consecutive audit cycles (v9.7.145a, v9.7.145b, v9.7.145c) produced packages where `SOURCE_CHECKSUMS_SHA256.txt` and `TIER_MANIFEST.txt` were stale, missing, or contained the wrong version header. The packaging seal was failing because mutable post-seal files were being included in the checksum set.

**Root cause:** `write_manifest()` was including `run_phase_receipts.jsonl`, `package_status.json`, and `claim_safety_status.json` in the checksum calculation. These files are written after the seal, so their checksums were computed before the final state was reached, causing mismatch.

**Fix (v9.7.146 PATCH-PACKAGING-SEAL):** `write_manifest()` and `write_checksums()` now exclude the same mutable post-seal files that `verify_checksums()` already excluded. This fixed the recurring checksum failures definitively.

---

### 8.2 — CHANGELOG had duplicate version headers
**Severity:** Low · **Discovered:** v9.7.148c audit

**What happened:** The top 29 lines of CHANGELOG.md contained two separate `# v9.7.148b` headers separated by a `---` divider. This happened because multiple CHANGELOG prepend operations ran against the same version without checking for an existing header.

**Fix (v9.7.148c BLOCK-B):** Merged into one entry. The CHANGELOG prepend pattern now checks for existing headers with the same version before prepending.

---

## 9 · Science and Analytical Errors

### 9.1 — Raw BGC counts used in figure keys instead of corrected counts
**Severity:** Medium · **Discovered:** v9.7.109 (Workstream A)

**What happened:** Several figure rendering paths in `figures_sapote.py` displayed raw `kcb_top` strings (unqualified compound names) rather than the provenance-aware `safe_kcb_display()` version. This was a claim-safety violation — compound names from KCB hits were being displayed as if they were product identifications.

**Fix (v9.7.103/v9.7.109):** `render_safe.safe_kcb_display()` wired into all figure rendering paths. Resolved MIBiG-line hits now show with "(similarity)"; raw KCB_TOP self-hits are qualified with "not product identity".

---

### 9.2 — NI-siderophore and NRP-metallophore scoring caused false lead suppression
**Severity:** Medium · **Discovered:** v9.7.122 · **Trigger:** AS-XXX BGC017 dogfood run

**What happened:** An early version of the iron/metal-acquisition exclusion rule (`BH-007`) incorrectly suppressed AB/AF scores for BGCs with co-present NRPS/PKS/RiPP leads alongside an iron-acquisition component. The rule was too broad — it downgraded the entire BGC rather than only the iron-acquisition capacity.

**Fix (v9.7.122 BH-007b):** The committed-class guard was added: a co-present NRPS/PKS/RiPP/lanthipeptide lead is preserved even when the iron-acquisition downgrade fires. The AS-XXX BGC017 lanthipeptide lead was correctly retained after the fix.

---

### 9.3 — Polyene CCTT trigger stacked bonuses instead of subsuming chemotype credit
**Severity:** Medium · **Discovered:** v9.7.120 · **Trigger:** scoring analysis of polyene BGCs

**What happened:** A confirmed polyene BGC could simultaneously receive the keyword scorer's bonus, the polyene chemotype credit (+22 AF), and the T43-PYE diagnostic trigger (+25 AF). All three stacked, producing unrealistically high AF scores for polyene BGCs.

**Fix (v9.7.120):** The corroborated T43-PYE diagnostic now subsumes the polyene chemotype credit. Net AF gain is `diagnostic_bonus − chemotype_credit`, not the full combined bonus.

---

## 10 · Documentation Issues

### 10.1 — Quick Guide §9 missing Citation-Compact Provenance heading
**Severity:** Low · **Discovered:** v9.7.148a (F002) · **Trigger:** test failure

**What happened:** `test_user_doc_citation_provenance_v97136.py` asserted that `"Citation-Compact Provenance and Citation Status"` appears as a heading in every current user doc. The Quick Guide had a §9 "Citation provenance" section but was missing the required heading format.

**Fix:** `### Citation-Compact Provenance and Citation Status` heading added above the existing §9 bullet list.

---

### 10.2 — Execution slice missing sourcing instruction for BLASTP action list
**Severity:** Low · **Discovered:** v9.7.148a (A004) · **Trigger:** hostile audit

**What happened:** §13 of the execution slice specified a "BLASTP action list" section for the compiled report but did not tell the LLM where to source the batch numbers and file paths. An executing LLM could fabricate batch numbers or silently omit the section.

**Fix:** Added to §13 section 8: "Source from `modeb_blastp/<BGC_ID>/` directories (produced by `mamey modeb-blastp`) or from the §16 queue in each Mode B card."

---

### 10.3 — No pre-condition gate on compiled report production
**Severity:** Low · **Discovered:** v9.7.148a (A005) · **Trigger:** hostile audit

**What happened:** §13 said "after completing all Mode B cards" but there was no mechanical gate preventing an LLM from producing the compiled report mid-session before cards were finished.

**Fix:** Pre-condition added to §13: "Do not produce this report until Mode B cards are complete for all top-N leads. If Mode B is still in progress, note the incomplete cards and state the report will be updated when they finish."

---

## Version History Synopsis

| Version | Theme | Key fixes / additions |
|---|---|---|
| v9.7.102–104 | Engine hardening | P0 crash fixes (missing imports, `_Record` attributes), correctness (GenBank coord fix, regex word-boundary), atomic writes |
| v9.7.105–106 | Gene context + quality gate | Closed-genome gene-context scoping fix; Mode B quality gate (FULL/SHALLOW/STUB three-tier depth classification) |
| v9.7.107–108 | Architecture-first classification | `architecture_first.py` — 30 pathway types, KCB-blind, boundary-aware; doc sweep |
| v9.7.109–111 | Claim-safety + figure subsystem | `safe_kcb_display()` wired everywhere; figure subsystem revived with schema adapter; Bunny Hop / Bug Hunt protocols |
| v9.7.112–114 | Mode B §1–§20 + enrichment | §1–§10 mandatory sections, write-time quality verdict, §11–§20 mandatory enrichment floor |
| v9.7.115–117 | Cross-strain cohort analysis | `cohort_cards`, `cross_strain_card_context`, `cohort_synthesis`; novelty-basis split guard; RG-GMCI cohort rollup |
| v9.7.118–120 | Reference docs + CCTT triggers | Engine reference docs (Math Reference Vol I–II, Plumbing Reference); three new CCTT triggers (polyene AF, glycopeptide AB, betalactone AB); triple-count clamp |
| v9.7.121–123 | Recall layer + linters | AB/AF antimicrobial recall layer; claim-safety linter; locator reconciliation gate; workbook populated-sheet gate |
| v9.7.124–126 | Card-time gating + seal-package | Card-time claim-safety + locator wiring; `mamey seal-package` CLI; figure-reference validation gate; deliverable-status table gate |
| v9.7.127–129 | Two-pathway detection | Gene-only two-pathway detector (`two_pathway.py`); `Two_Pathway_Flag` triage column; BGC decomposition module (`bgc_decomp.py`) |
| v9.7.130–131 | Domain classifier expansion | `lasso`, `thioamide`, `phosphonate` new classes; hierarchical RiPP-family coherence |
| v9.7.132–134 | Cross-assistant bootstrap | AS-XXX SPAdes contig fix; `000_READ_ME_FIRST_CHATGPT_CLAUDE.md`; `CLAUDE_START_HERE.md`; smoke-first default |
| v9.7.135–137 | ChatGPT handback | Exactly-8 unique next-paths rule; release polish |
| v9.7.138–140 | Four-tier consolidation | C1–C4 release-identity; public/private leak-safety; surrogate gate |
| v9.7.141–142 | ChatGPT operational reliability | Smoke-first first-run guard; BLASTP evidence store; `bgc-blastp-panel`; `blastp-followup` |
| v9.7.143–144 | Mode B corrective protocol | Mode B §1–§20 canonical contract; Wise Fragmented PKS workflow; Mode B section lock |
| v9.7.145 | Node notation + locus maps + emitter | `node_notation_validator`; `locus_map.py` SVG renderer; `BlastpBatchEmitter`; trigger routing |
| v9.7.146 | Packaging seal | `write_manifest()` mutable-file exclusion (root cause of recurring checksum failures); delivery gap + interpretive depth |
| v9.7.147 | Execution slice + edge BGC equality | `CHATGPT_EXECUTION_SLICE_v97147.md` (replaces slim kernel); edge/FC BGCs get full Mode B depth; §28/§30 required |
| v9.7.148 | Auto-figures + BLASTP auto + compiled report | Gold figure suite fires automatically; `modeb-blastp` CLI; compiled report as required deliverable; mycofactocin disambiguation; BGC044 reclassification |
| v9.7.148a | Audit closure | Dummy checksum fix; f-string bug; dead parameter; docstring corrections |
| v9.7.148b | Node citation enforcement + sync_version suffix | §15 hard node citation rule; `node_citation_map.json`; sync_version regex letter-suffix fix |
| v9.7.148c | RELEASE_MANIFEST cleanup + cover overlap fix | Stale refs removed; CHANGELOG deduplicated; cover overlap in PDF explained and patched |

---

*Maintained by the / . Add entries when a bug is found and fixed — the root cause is always more useful than the symptom.*

*Last updated: 2026-06-29 · Sapote–Mamey v9.7.148c*

## 11 · Offline Operation Misunderstanding

### 11.1 — Audit chat parsed raw antiSMASH JSON instead of running Mamey
**Severity:** High · **Discovered:** v9.7.148c cycle · **Trigger:** audit chat reporting "network is disabled, can't pip-install"

**What happened:** An audit chat session received the Mamey bundle but did not run the engine. It reported: *"Network is disabled in this environment so I can't pip-install the dependencies Mamey needs. I was parsing the raw antiSMASH JSON directly, which gives me class labels and node lengths but none of the scored outputs: no triage board, no AB/AF scores, no CCTT triggers, no FLBR census, no boundary calculations, no lead tiers."* It then produced a raw inventory from the antiSMASH JSON instead of a Mamey package.

**Root cause:** The audit chat assumed that `pip install` requires internet access. It does not — the bundle is specifically designed for offline installation. `ijson` ships vendored inside the bundle (`mamey/_vendor/ijson`). `openpyxl` installs from a local path. Companion wheels (biopython, pytest, matplotlib, numpy) ship alongside the bundle for `pip install --no-index --find-links ./wheels`. No network call is made during any of these steps.

The `CHATGPT_START_HERE.md` run command block showed `pip install` commands without a prominent "this works offline" callout, so the audit chat concluded the commands would fail.

**What a raw-JSON parse produces vs what Mamey produces:**

| Output | Raw antiSMASH JSON | Mamey package |
|---|---|---|
| BGC class labels | ✅ (antiSMASH raw) | ✅ (validated + corrected) |
| Node/contig names | ✅ | ✅ |
| Corrected BGC count | ❌ | ✅ (Interior + ½·Edge + ¼·FC) |
| AB/AF/WL scores | ❌ | ✅ |
| CCTT triggers | ❌ | ✅ |
| FLBR fragmentation rescue | ❌ | ✅ |
| RGGMCI split-cluster pairs | ❌ | ✅ |
| Lead tier ranking | ❌ | ✅ |
| KCB misanchor detection | ❌ | ✅ |
| Standing rule exclusions | ❌ | ✅ |
| Mode B cards | ❌ (blocked by gate) | ✅ |
| Triage board | ❌ | ✅ |

A raw-JSON parse is not a Mamey package. Any analysis built on it is missing ~80% of the pipeline's output and should not be used for Mode B or scientific conclusions.

**Fix:** `CHATGPT_START_HERE.md` now prominently states before the run commands:
> The engine runs fully offline — no internet required. Install from the bundle root: `pip install -e . --break-system-packages --no-index`. Do NOT parse raw antiSMASH JSON as a substitute — that is not a Mamey package.

**Install commands for a fully offline session:**
```bash
pip install -e . --break-system-packages --no-index        # core engine
pip install --no-index --find-links ./wheels biopython      # optional robust GBK parsing
pip install --no-index --find-links ./wheels matplotlib numpy  # optional figures
```

## 12 · Multi-Strain Batch Workflow Gap

### 12.1 — Testing chat ran four strains individually instead of using the intake harness
**Severity:** High · **Discovered:** v9.7.148e · **Trigger:** four-strain batch session

**What happened:** A testing chat session with four antiSMASH ZIPs ran `mamey run` on each strain one at a time, then stalled when trying to begin Mode B. It reported: "I have the manifests but not the full package outputs. The cards would need to be authored from the raw GBKs... Give me the strain metadata and I can start immediately." It then asked the user for strain metadata three times.

The chat did not know: (1) `tools/intake_harness.py` exists for multi-strain batching; (2) strain metadata is already in the package at `_1_intake.json`; (3) Mode B requires `mamey mode-b --package <pkg> --top-n N`, not manual GBK parsing; (4) §21–§30 are required per the execution slice.

**Root cause:** The execution slice had no dedicated multi-strain workflow section. The only reference to batch runs was a single sentence in CHATGPT_START_HERE: "use `tools/intake_harness.py --resume`" with no command syntax or explanation.

**Fix (v9.7.148e):**
- Execution slice §16: full multi-strain batch protocol with exact commands for intake harness, per-strain validate, per-strain mode-b, and explicit statement that metadata comes from the package not the user
- CHATGPT_START_HERE: single-strain callout replaced with full batch command block and `mode-b` follow-up

**The correct four-strain workflow:**
```bash
# Step 1 — install (once)
pip install -e . --break-system-packages

# Step 2 — run all strains
python tools/intake_harness.py   --inputs A.zip B.zip C.zip D.zip   --outdir runs/ --registry runs/registry.csv   --metrics runs/metrics.csv --release PRIVATE --mode gold   # smoke mode was retired v9.7.161; intake_harness --mode now accepts only {standard,gold}

# Step 3 — validate each
python -m mamey validate runs/<strain_id>/package

# Step 4 — Mode B per strain
python -m mamey mode-b --package runs/<strain_id>/package --top-n 5 --outdir mode_b/<strain_id>/
```

**Never** author Mode B cards from raw GBKs without running the engine first. The engine produces AB/AF scores, CCTT triggers, corrected BGC counts, KCB crosswalk, standing-rule exclusions, and RGGMCI pairs — none of which are available from raw antiSMASH output.

## 13 · Mode B Section Scope Confusion

### 13.1 — Testing chat claimed §21–§30 do not exist
**Severity:** High · **Discovered:** v9.7.148g · **Trigger:** four-strain batch Mode B session
**Resolved structurally in v9.7.150d (W9):** doc-only fixes (the §0/§9/§16 notes below) did not
fully close this failure surface — a chat's prior-session memory of the historical §1–§20 scaffold
can persist even when the current docs are correct. `mamey.modeb_structure_gate` now validates
every card against the canonical §1–§30 contract before it is persisted via any ingest path
(`ingest_one_card`, `auto_detect_ingest`, `ingest_receipt`); cards built on the legacy scaffold are
refused by default (override: `--force-structure`). `mamey emit-modeb-template` pairs with the gate
by emitting a structurally-valid skeleton so the chat authors interpretation, not structure. The
gate's test suite uses a synthetic fixture named "BGC033" exhibiting the legacy-scaffold pattern —
this is a test fixture identifier, not a reference to a real prior incident with that BGC number.

**What happened:** A testing chat session told the user "§21–§30 don't exist in the canonical contract — the card format runs §1–§20." This is wrong. §28 (Evidence provenance ledger) and §30 (Experimental decision tree) are required for every completed Mode B card. §21–§27 and §29 are conditional by BGC class.

**Root cause:** The execution slice §0 authority order lists `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` as item 2. That document says "Full Mode B means a BGC-specific §1–§20 card" and lists exactly 20 sections with no mention of §21–§30. A chat that reads the contract but doesn't reach the §9 and §16 overrides in the 619-line execution slice will conclude §1–§20 is the complete specification.

The §16 note added in 148e says "§21–§30 are required... the execution slice supersedes FULL_MODEB_20_SECTION_CONTRACT — if that document says §21–§30 don't exist, this slice takes precedence." But this is 600 lines into the execution slice, after the authority order that points to the contract.

**Fix (v9.7.148g):**
- Supersession banner added to top of `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md`: explicitly states §28 and §30 are required, §21–§30 conditional sections exist, execution slice wins
- Same banner added to `docs/MODE_B_20_SECTION_CANONICAL_TITLES.md`
- Execution slice §0 item 2 updated to state directly: "§28 and §30 are required for every card; §21–§30 conditional sections are defined in §9 of this slice"

**Complete Mode B = §1–§20 + §28 + §30 (mandatory) + applicable §21–§27/§29 (conditional by class)**

## 14 · BLASTP Panel FASTA Header Parsing

### 14.1 — `_parse_fasta` gene tag regex consumed entire header tail on space-delimited format
**Severity:** High · **Discovered:** v9.7.150 (Opus W7) · **Trigger:** real-format header audit

**What happened:** `_parse_fasta()` in `mamey/modeb_blastp.py` used `r"gene=([^|]+)"` to extract the locus tag from FASTA headers. This regex matches everything except a pipe character. On pipe-delimited headers (`>strain|BGC_ID|slot=N|role=...|gene=<tag>|node=...`) this worked correctly — the next `|` stopped the capture. On AS-XXX-style space-delimited headers (`>ctg107_3 gene=ctg107_3 BGC=BGC003 length=619 product=hypothetical protein`) there is no `|` after `gene=`, so the capture group consumed the rest of the line. The resulting "gene tag" was `"ctg107_3 BGC=BGC003 length=619 product=hypothetical protein"` — garbage, not a usable locus tag.

**Impact:** Any FASTA emitted in space-delimited format and re-parsed by `_load_panel_sequences()` would have its sequences keyed under garbage tags, silently breaking the BGC-filtering step in `emit_for_bgc()`.

**Fix:** Regex changed to `r"gene=([^|\s]+)"` — stops at whitespace OR pipe. Both header formats now parse correctly. 4 tests added covering pipe format, space format, mixed-format files, and multiline sequence wrapping.

**Production audit needed:** Any package built before v9.7.150 that ran the BLASTP panel workflow (`mamey modeb-blastp`) on a space-delimited FASTA should be checked — sequences may have been mis-keyed. Re-running `emit_for_bgc()` on an existing package with this fix will now correctly key sequences; any cached BLASTP evidence store entries from before the fix should be regenerated if they came from a space-delimited source. No production artifacts from this development arc were affected (verified: no `modeb_blastp/` outputs exist yet from before v9.7.150).

## 15 · Bug Hunt Findings (v9.7.150b → v9.7.150c)

### 15.1 — runs_dir validation regressed the common single-strain case
**Severity:** High · **Discovered:** v9.7.150c hostile self-audit · **Trigger:** re-examining the W1 wishlist's "Item 1" fix from earlier the same day

**What happened:** The fix applied earlier today for the `runs_dir` path assumption bug validated the inferred `<outdir>` path by checking whether any *other* strain directory existed alongside the current one (`any(... if d != package_dir.parent.name)`). A genuine single-strain run — the common case — has no sibling strain directory by definition, so this check always returned `False` and silently fell back to the wrong path (`package_dir.parent` instead of `package_dir.parent.parent`) even when the standard layout was completely correct. The fix written to solve a rare non-standard-layout problem broke the standard layout instead.

**Fix:** Validation changed to check the structural property that actually indicates the standard layout — `package_dir.name == "package"` and `package_dir.parent.parent.is_dir()` — rather than requiring evidence of other strains. Verified against both the standard single-strain case (correctly uses `parent.parent`) and a non-standard case (correctly falls back with a written note).

**Lesson:** A "let's check it's the real thing" validation needs to check a property of the *thing itself*, not collateral evidence that only exists in a multi-instance scenario. The single-instance case is usually the majority case and must be tested explicitly, not assumed to be covered by a check designed for the plural case.

### 15.2 — JUDGMENT PENDING banner sync was one-directional
**Severity:** Medium · **Discovered:** v9.7.150c hostile self-audit

**What happened:** `_clear_judgment_pending_banner()` (now `_sync_judgment_banner()`) only handled PENDING → COMPLETE. If a Mode B card is later invalidated — e.g. the BGC044 ranthipeptide→mycofactocin reclassification pattern documented in issue 2.1 — and `judgment_status` regresses from COMPLETE back to IN_PROGRESS, nothing restored the PENDING banner. A user could see a stale "✅ JUDGMENT COMPLETE" header on a package that the register itself says is back in progress.

**Fix:** Banner sync made bidirectional. Both directions verified: PENDING→COMPLETE rewrites the header correctly; COMPLETE→IN_PROGRESS restores the original PENDING header and removes the COMPLETE body marker.

### 15.3 — ingest_one_card overloaded BAD_PATH for two different failure modes
**Severity:** Low · **Discovered:** v9.7.150c hostile self-audit

**What happened:** `ingest_one_card()` returns `status: "BAD_PATH"` both when the `--card` file itself can't be found/read AND when `record_mode_b()` raises during the actual write step. A caller checking `status == "BAD_PATH"` to mean "the file path argument was wrong" would be misled in the second case — the file was fine; the write failed for an unrelated reason (disk error, internal claim-safety gate, etc.).

**Fix:** New status `RECORD_FAILED` for write-time failures, distinct from the file-not-found `BAD_PATH`. The exception message is now captured in an `error` field. Verified the CLI dispatch (`ingest_receipts_command`) still correctly maps any non-`RECORDED` status to exit code 3 — the rename didn't require a dispatch change since the success check was always `== "RECORDED"`, not an exhaustive switch on failure modes.

### 15.4 — Non-finding: searched for sibling occurrences of the W7 FASTA regex bug
**Severity:** N/A (clean) · **Discovered:** v9.7.150c hostile self-audit

Searched the codebase for other unbounded-capture regex patterns matching the same shape as W7's bug (`[^delimiter]+` anchored on only one side). Found one structurally similar-looking pattern in `source_scans.py` (`_KCB_COMPOUND_EXTRACT`) but confirmed it is anchored on both sides (`\s*\|\s*([^|]+?)\s*\|`, non-greedy, both delimiters required) — a missing trailing delimiter causes a failed match, not an over-consuming one. Not the same bug class. No further instances found.

## 16 · Real Pytest Run Findings (v9.7.151 → v9.7.151a)

### 16.1 — modeb_structure_gate.py: empty context dict treated as "real context with a gap" instead of "no context"
**Severity:** High · **Discovered:** v9.7.151a · **Trigger:** first genuine full pytest run of the session (2,480 tests collected) surfaced this; the stdlib test harness used throughout this session could not reproduce it since it never exercises the conditional-predicate branch with a real-but-empty context dict.

**What happened:** `lint_card()`'s conditional-section branch checked `if bgc_context is not None:` to decide whether to enforce conditional sections as ERROR (real context) or downgrade them to WARN (no context — predicate not evaluated). But `_bgc_context_from_triage()` — the canonical context builder used by all three ingest paths — returns `{}` (not `None`) when no triage row matches, exactly the situation the WARN-only path is meant to cover. Since `{} is not None` evaluates `True`, every card ingested without a matching triage row took the strict ERROR path instead. The §24 predicate (`novel_or_no_mibig`) fires on any context missing a `kcb_top` field — which an empty `{}` always is — so nearly every minimal or synthetic-fixture card was refused with a phantom "missing §24" error, even though no real evidence existed either way.

**Fix:** Branch condition changed from `if bgc_context is not None:` to `if bgc_context:` (truthy check) — both `None` and `{}` now correctly route to the WARN-only path. Verified against three cases: no context (`None`), empty context (`{}`), and a real context with a genuine predicate-firing gap — only the third case still correctly produces an ERROR.

**Why the earlier stdlib-harness testing in this session missed it:** every manual functional test written during the session either passed `bgc_context=None` explicitly or never exercised the real `_bgc_context_from_triage()` path end-to-end with a deliberately-empty result. The bug only surfaces when a real ingest path builds context from a triage board that doesn't contain the BGC being ingested — a realistic scenario a synthetic unit test naturally avoids unless it specifically constructs that case.

### 16.2 — Test fixtures across three ingest test files used pre-W9 minimal stub content
**Severity:** Medium (test-only, no production impact) · **Discovered:** v9.7.151a

`test_auto_detect_ingest.py`, `test_ingest_one_card.py`, and `test_mode_b_receipt.py` were written for W4 (v9.7.149c), before the W9 structure gate existed. Their helper functions defaulted to minimal placeholder content like `"## Mode B card content\n\nReal content here."` — fine when ingest *mechanics* (register transitions, idempotency, BGC-ID resolution) were the only thing under test, but the W9 structure gate (added v9.7.150) now lints every card before persisting, and these placeholders are nowhere close to §1–§30-valid.

**Fix:** New shared helper `tests/_modeb_card_fixtures.py::valid_modeb_card_stub()` builds a genuinely valid card directly from the live contract JSON (so it tracks the contract automatically rather than hand-copying section titles). Wired into all three affected files as the new default; explicit minimal-content negative tests (empty card, whitespace-only, bare-body-no-header) were preserved deliberately rather than "fixed away."

### 16.3 — compilation_gate.py test fixture used inline heading+prose format the gate's regex doesn't match
**Severity:** Medium (test-only) · **Discovered:** v9.7.151a

`tests/fixtures/compilation_gate/full_compendium.md` used `**§1 Title** — prose on the same line`. The structure gate's heading regex requires the heading to be alone on its line (`\s*$` after the optional closing `**`); prose appended on the same line never matches, so the whole card registered as `NO_HEADINGS_DETECTED`. Regenerated the fixture with headings and prose properly separated; also widened section coverage from §1–§10-only (the original pre-W9 fixture) to the full 22 always-required sections, and confirmed the gene-table row count and section-density floor (raised 6→18 earlier this session) are both genuinely satisfied, not just nominally present.

### 16.4 — Test asserted .faa extension on a function that emits .fasta
**Severity:** Low (test-only typo) · **Discovered:** v9.7.151a

`test_emit_for_bgc_writes_fasta_files` checked `out.glob("*.faa")`, but `mamey.modeb_blastp.emit_for_bgc()` genuinely writes `<BGC_ID>_batchN.fasta`. The `.faa` extension is correct for the *input* panel files (`*_curated_N_for_BLASTP.faa`) but wrong for the *output* batch files. A pure test-assertion bug, not a production issue — fixed both call sites checking emitter output.

### 16.5 — Two modeb_workflow tests reported as intermittent — confirmed not reproducible in isolation
**Severity:** N/A (unresolved, flagged for next full run) · **Discovered:** v9.7.151a

`test_npdc041969_comparator_workflow_triggers` and `test_large_protein_misannotation_guard_triggers` were reported failing in a full pytest run but passing standalone. Both functions under test (`detect_comparator_workflows`, `large_protein_misannotation_warning`) are pure — operate only on their DataFrame argument, no module-level mutable state. Confirmed both pass cleanly in isolation; grepped the full test suite for `pd.set_option`/`pandas.set_option`/`pd.options` mutation (a common cause of this exact "isolation passes, full-suite fails" signature with pandas) and found none. No fix applied — nothing to fix without a reproducible failure. Flag for the next full pytest run: if it recurs, capture the full traceback and the preceding 2-3 tests in execution order to look for shared fixture/import-order effects.

## 17 · Documentation Integration — docs/batches/ and a Latent Redaction-Policy Mismatch

### 17.1 — verify_tier_derivation.py hardcoded a stricter redaction policy than the real tier-build script uses
**Severity:** High · **Discovered:** v9.7.151b · **Trigger:** integrating a new 18-document batch series (`docs/batches/`) that, for the first time in this bundle's history, named specific SID strain numbers (SID8370, SID8371, SID8375) in prose.

**What happened:** `tools/verify_tier_derivation.py`'s `redact_text()`/`redact_py()` wrappers called the shared redaction function with `as_only=False`, with a comment claiming this "mirrors the code/sid public-tier scrub (SID + AS both redacted)." That claim was wrong. Every real call site in `tools/make_public_tier.sh` — for every tier, every time — passes `--as-only` to `redact_public_tier.py`, whose own comment states plainly: "`--as-only` keeps public SID (Chevrette 2019) intact." SID strain identifiers are genuinely public (the Chevrette 2019 attine ant antiSMASH dataset) and were never meant to be redacted in any tier.

Because no prior bundle content happened to name a specific SID number in prose, this mismatch sat latent — `verify_tier_derivation.py` was checking against a stricter, never-actually-applied policy and would have produced a false `FATAL: code tier is NOT an exact redaction-view of the private source` on the very first document that triggered it. That document turned out to be `docs/batches/batch12_figure_system_one_pager.md`, which uses SID8370/8371/8375 as illustrative example strain IDs in a CLI command and a sample CSV.

**Fix:** Both wrappers changed from `as_only=False` to `as_only=True`, matching the real tier-build policy exactly. Verified: the official `tools/make_public_tier.sh code` run now passes the parity gate cleanly with the new batch documents present; SID numbers survive redaction (correctly), private AS-series numbers are still redacted (correctly, unaffected by the fix).

**Regression guard:** `tests/test_verify_tier_derivation.py` (4 tests) — pins SID-survives-redaction and AS-still-redacted behavior at the function level, plus a source-level check that the verifier's call sites can't silently regress back to `as_only=False` (carefully scoped to match only live code, not the explanatory comment that legitimately quotes the string while describing this very bug).

### 17.2 — New documentation: docs/batches/ (18 of a planned 28-document set)
**Severity:** N/A (feature, not a bug) · **Added:** v9.7.151b

A new plain-English reference document set was integrated: `docs/batches/batch06`, `11`, `12`, `14` (from a first set of 14), and the complete second set `batch15`–`batch28` (14 documents). Each distills existing scattered bundle source documentation (the glossary, execution slice, DAPR framework, literature protocol, etc.) into single-purpose quick references — claim-safety field manual, BGC class reference, RGGMCI split-cluster guide, multi-strain comparative claims, onboarding packet, session handoff protocol, and more.

**Known gap:** batches 01, 02, 03, 04, 05, 07, 08, 09, 10, and 13 were referenced throughout this set's own navigation index (`batch15_master_index.md`) but were never delivered to this bundle — 10 of the planned 28 documents remain outstanding. The master index document itself also has an internal numbering inconsistency (its own "complete document list" table is off-by-one from the actual filenames shipped) — both gaps are flagged explicitly in a status note added to the top of `batch15_master_index.md` rather than silently glossed over.

### 17.3 — make_public_tier.sh's strict parity gate incorrectly scoped to both code AND clean tiers
**Severity:** High · **Discovered:** v9.7.151b, same session as 17.1 · **Trigger:** re-cutting all four tiers after the 17.1 fix — `code` and `sid` passed, `clean` failed with the same class of false-positive drift report.

**What happened:** `clean` (the "analysis-free" tier) applies an *additional* transformation beyond the base `redact_public_tier.py --as-only` pass: a direct `sed -E 's/SID[0-9]{2,}/SID-XXX/g'` step that anonymizes SID strain numbers too (a uniformity scrub, not a secrecy one — SID is public; see the script's own comment at the point of that sed call). This makes `clean` not a pure single-function redaction-view of the private source, the same structural reason the script's authors had already correctly excluded the `sid` tier from this gate. But the gate's `if` condition still included `clean` alongside `code`, so it compared `clean`'s doubly-transformed output against `verify_tier_derivation.py`'s single-function redaction baseline and reported false drift on the same `docs/batches/batch12_figure_system_one_pager.md` SID-number content that triggered 17.1.

**Fix:** Narrowed the gate's `if` condition to `code` only. Verified: `clean` tier now cuts cleanly; `code` tier still correctly gated (re-confirmed passing); sanity-checked the gate still genuinely catches real injected drift in a `code`-tier staging copy (not just always-passing).

**Pattern note:** both 17.1 and 17.3 are instances of the same root cause — a verification/gating tool built with an assumption ("this tier is a pure redaction-view") that was true when the tool was written but silently became false as the tier-build script gained additional per-tier transformation steps over time, with nothing keeping the two in sync. Worth a standing note for future tier-script changes: any new per-tier transformation step needs an explicit decision about whether the strict parity gate still applies to that tier, not an implicit assumption either way.

