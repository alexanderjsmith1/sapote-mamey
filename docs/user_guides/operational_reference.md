# Sapote–Mamey Operational Reference
## Workflow, Protocols, and Standard Operating Procedures
**Bundle v9.7.319 · Engine 1.9.111**
Hamilton, Ontario

*Sourced from: `docs/HOW_TO_USE.md`, `docs/GUIDE/01_User_Manual.md`, `docs/GUIDE/02_Quick_Guide.md`, `docs/SINGLE_STRAIN_QUICKSTART.md`, `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md`, `docs/ONLINE_BLASTP_PROTOCOL.md`, `docs/BERT_MODE_PROTOCOL.md`, `docs/LITERATURE_SEARCH_PROTOCOL.md`, `docs/RELEASE_CHECKLIST_v9.md`. All content from source files; no inference.*

---

## Section 1: Installation Reference

### Python and environment requirements

Python 3.10 or later required. Python 3.12 recommended — matches compiled wheel platform tags. Check: `python3 --version`. The bundle operates from within its own directory.

```bash
unzip sapote-mamey-v9.7.319-CODE-20260907v97414a.zip
cd sapote-mamey-v9.7.319-CODE-20260907v97414a
pip install -e .
# On managed/Debian systems:
pip install -e . --break-system-packages
```

This installs the `mamey` command and the two core dependencies (openpyxl for workbooks; ijson is vendored inside the bundle and works offline automatically).

### Addon installation

```bash
bash install_sapote_addons.sh           # auto-discovers every attached addon part
bash install_sapote_addons.sh /path/    # or point at a specific directory
```

The installer pools all `.whl` files it finds across all named paths and installs them in a single `pip install --no-index --find-links` call. Core science stack (pyhmmer, pyskani, biopython, etc.) must install before figure stack (matplotlib, numpy, pandas, scipy) because several figure modules import from science stack packages. The installer handles this ordering.

**Biopython filename note:** the wheel filename must use dots, not underscores, in the version and platform tags. A file transfer that replaced dots with underscores must be renamed before installation: `biopython-1.87-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` (correct form).

### Verification

```bash
mamey doctor                          # pre-flight: Python, deps, permissions, bundle integrity
python3 tools/sync_version.py --check # → engine 1.9.111, bundle 9.7.241
python3 -m pytest -q                  # 3064 passed / 157 skipped / 0 failures
```

The startup banner on every `mamey run` prints a dependency line showing which optional stack is available. `ijson(vendored)✓` means the pure-Python bundled copy is active; `ijson(system)✓` means the C-backend system install is active (faster). Both are correct.

### Bundle tiers

| Tier | Contents | Use for |
|---|---|---|
| CODE | Full engine + docs + analysis tools | Internal working tier — all analysis |
| CODE-analysis-free | Engine code only | Testing and patching without analysis extras |
| SID-public | AS-strain identifiers stripped | External sharing |
| MERGED-PRIVATE-scaffold | Full cross-strain merge scaffold | PRIVATE by construction — never distribute |

Use CODE for all internal analysis. `AS-` / `AJS-` / `PENDING-` strains are unpublished and always PRIVATE. `SID-` / `WW-` are public.

---

## Section 2: Standard Run Sequence

The canonical command for a single strain:

```bash
python -m mamey run \
  --input-zip AS-XXX_antismash.zip \
  --strain AS-XXX \
  --display "Streptomyces sp. AS-XXX" \
  --taxonomy "Streptomyces sp." \
  --source "Apis mellifera, Ontario" \
  --release PRIVATE \
  --mode gold \
  --json-evidence bounded \
  --outdir runs/
```

**Required flags:**
- `--input-zip` — antiSMASH output ZIP (not a raw FASTA; see Common Mistakes §1)
- `--strain` — meaningful label, not an NCBI accession (see Common Mistakes §3)
- `--release PUBLIC|PRIVATE` — hard-guarded; AS-/AJS-/PENDING- must be PRIVATE

**Key optional flags:**
- `--mode gold` — enables gene-by-gene Mode B depth layer; recommended for strains headed to deep analysis
- `--json-evidence bounded` — enables RiQ scores and A-domain substrate predictions from antiSMASH region JSONs; falls back to `off` when ijson unavailable (silent fallback — check the startup banner)
- `--json-evidence off` — fastest; excludes RiQ and A-domain data
- `--capped-session` — applies timeout-safe defaults (suppresses figures, caps streaming); for resource-limited environments
- `--taxonomy` — prevents the `.` display name (see Common Mistakes §7)
- `--source` — provenance string; when absent, habitat falls to ENGINE_DEFAULT_PLACEHOLDER

**Validate immediately after run:**
```bash
python -m mamey validate runs/AS-XXX/package
```

Status vocabulary: `MAMEY_COMPLETE` (all required files present and checksums valid) · `MAMEY_COMPLETE_WITH_ISSUES` (core valid, peripheral issues logged) · `VALIDATION_FAIL` (do not use — diagnose issue log first).

**Post-seal figures:**
If the run used `--capped-session` or figures were skipped for any reason (`NO_FIGURES_RENDERED.md` present):
```bash
python -m mamey render-all-figures --package runs/AS-XXX/package
```

### Single-strain quickstart (abbreviated path)

For one strain, the minimum working sequence:

1. `python -m mamey run --strain <ID> --input-zip <antismash.zip> --mode gold --outdir work/<ID>`
2. `python -m mamey validate --package work/<ID>`
3. `mkdir -p cohort && python tools/ingest_package.py --package work/<ID> --banked-dir cohort`
4. `python tools/build_figures.py --banked-dir cohort --out fig/` (if cohort figures needed)
5. Mode B: `python -m mamey emit-modeb-template --package work/<ID>/package --bgc BGC001`

**Single-strain caveats:** cohort-local computations (product-class matrices, cross-strain findings) are degenerate at N=1 — read them as single-strain summaries, not cohort statistics.

### Cohort (multi-strain) sequence

Run every strain through Mamey before any Mode B interpretation. One strain at a time.

```
run strain → validate → bank → update master workbook → next strain
```

The cross-strain pattern needs to be visible before spending judgment time on individual strain deep dives. Mode B priorities should be set after reviewing the cohort triage board, not before.

**Building the master workbook (supported path):**
```bash
# Option A: one-step intake
python tools/mamey_intake.py --packages runs/ --banked-dir cohort/ --workbook project_master.xlsx

# Option B: explicit two-step
python tools/ingest_package.py --package runs/AS-XXX/package --ww WWGP0000000 --merge --banked-dir cohort
python tools/build_workbook.py --workbook project_master.xlsx --banked-dir cohort --full
```

**Do not use `mamey/master_workbook.py` (`--master` flag) directly** — it is mid schema-migration and emits doubled, non-conformant workbooks. The supported path is `ingest_package.py → build_workbook.py` or `mamey_intake.py`.

`build_workbook.py --full` order (each step idempotent): deep-data bank → marker bank → `build_master` → cross-strain overlays → DAPR boards → D5/Activity_Ref → Lead_Board with RG-GMCI rescue flags + Mode B verdict fold.

---

## Section 3: JSON Evidence Modes and Deep Sheet Completeness

The `--json-evidence` setting determines which workbook sheets can be fully populated.

| Mode | What it enables | What it omits |
|---|---|---|
| `off` | Fastest; KCB from TXT only; no RiQ | RiQ scores, A-domain substrates, active sites, RiPP cores |
| `bounded` (default) | Streams region JSON; enables RiQ; A-domain, active site, RiPP from JSON | Nothing — recommended default |
| `full` | Richest active-site and substrate data from full JSON parse | Slower on large genomes |

**GBK recovery note:** three of the four fine workbook sheets do NOT require bounded mode. antiSMASH writes A-domain substrate predictions, KR active-site/stereochemistry calls, and protocluster class+category into region GBKs regardless of json mode. So `Gene_NRPS_PKS_Substrates`, `Gene_Active_Sites`, and `BGC_Class_Predictions` are recoverable offline from GBKs (tagged `Source = GBK-offline`). Only `Gene_RiPP_Cores` genuinely requires the region JSON.

The `OFFLINE-LIMITED` line from `build_deep_data.py` lists specific strains whose fine sheets are empty due to offline runs. To recover: re-run those strains on a networked machine with `--json-evidence bounded`.

---

## Section 4: Fragmentation-Robust Normalization

Raw genome-wide gene counts and raw BGC counts both inflate with assembly fragmentation — partial genes at contig ends are double-counted. Dividing by a fragmentation-sensitive denominator compounds the problem.

**Tested normalization denominators** (correlation with log10 contig count across the cohort):

| Denominator | Correlation with fragmentation | Verdict |
|---|---|---|
| Raw total BGC count | r = +0.42 | Inflates — avoid |
| NRPS count | r = +0.42 | Inflates (large clusters split) — avoid |
| Corrected BGC count | r = −0.48 | Over-deflates — avoid |
| **ectoine + NAPAA** | **r = −0.02** | **Robust — use** |
| Halogenase count | r = +0.09 | Robust but ecologically variable |

`build_chitinase_screen.py` uses `chit_per_unit = chitinase_count / (ectoine + NAPAA)` and flags outliers (|z| > 1.3). Strains missing both ectoine and NAPAA are flagged `no_norm_ref` rather than scored.

**Generalisation:** any genome-wide count can be normalized to the ectoine+NAPAA single-copy unit for fragmentation-robust cross-strain comparison. The denominator works because ectoine and NAPAA are single-copy and do not split on assembly fragmentation.

**Saccharide raw count rule:** the raw `saccharide` count is excluded from headline class rankings. antiSMASH `saccharide` fires on glycosyltransferase/NDP-sugar tailoring machinery, producing a count dominated by tailoring arms and sugar-metabolism islands. `build_saccharide_triage.py` splits saccharide regions into: `CANDIDATE_PRODUCT` (standalone with named KCB anchor → the reportable count), `UNCHARACTERIZED_STANDALONE` (large, no anchor), `TAILORING` (report under scaffold class), `MACHINERY` (excluded). Use the `CANDIDATE_PRODUCT` count in all prevalence reports.

---

## Section 5: Online BLASTp Protocol

Source: `docs/ONLINE_BLASTP_PROTOCOL.md`. The third evidence channel for every Mode B lead BGC.

### Why it exists

Mode B §4/§8 authored only from antiSMASH Pfam calls and KCB scores makes two concrete errors:
1. **KCB score taken as identity** — a high aggregate KCB with low gene coverage is not a compound anchor
2. **antiSMASH Pfam calls accepted without validation** — on BGC006/AS-XXX, BLASTp overturned two of ten domain calls: `Beta-lactamase` → EstA serine hydrolase, `Phenol_Hydrox` → ferritin-family protein. A third was sharpened to a specific named resistance enzyme.

Per-gene BLASTp is the independent channel that catches both. It also resolves strain taxonomy from the consensus top-hit organism across all genes.

### Scope

Run for every BGC receiving a full Mode B card. Every CDS is eligible. Priority order when time-bounded: (1) catalytic core (KS/CLF/KR/ACP, NRPS C/A/T modules, RiPP precursor + cyclodehydratase), (2) tailoring enzymes, (3) transport + resistance, (4) regulators, (5) accessory/hypothetical.

### The recipe

**Batch size rule (current, v9.7.252):** a submission closes on protein count **or** a 30,000-aa `RESIDUE_BUDGET`, whichever hits first. `MAX_BATCH` is 30 (hard clamp), `DEFAULT_BATCH` is 10 (the courteous default when a caller omits `batch_size`), and `SUBMIT_GAP_S` spaces submissions. *(History: the batch cap was ≤10 pre-v9.7.245 — verified timing then: 61 proteins (21,756 aa) still WAITING at 2.5 min+, 10 proteins (2,943 aa) READY at ~2.5 min — then raised to 30 on the strength of AS-XXX's 878-protein run, with `RESIDUE_BUDGET` added in .252 so large-residue batches close early regardless of count.)*

**Large protein handling:** proteins >2,500 aa (`GIANT_AA`) run solo, never inside a batch of small genes.

**Submit:**
```python
params = {"CMD":"Put", "PROGRAM":"blastp", "DATABASE":"nr",
          "QUERY": fasta_text,  # ≤10 sequences, multi-FASTA
          "HITLIST_SIZE":"3", "EXPECT":"1e-5", "tool":"SapoteMamey"}
# POST to https://blast.ncbi.nlm.nih.gov/Blast.cgi
# → extract RID from response
```

**Poll (≥30 s interval):** `CMD=Get&RID=<rid>&FORMAT_OBJECT=SearchInfo` → Status=WAITING|READY|FAILED|UNKNOWN. Expect READY at ~2.5 min for a 10-protein moderate batch.

**Retrieve:** `CMD=Get&RID=<rid>&FORMAT_TYPE=XML` → parse with `Bio.Blast.NCBIXML`. **CRITICAL:** records return in submission order — map back to locus tags by index, not by the query name in the XML (round-trip is unreliable).

**Fields to record per gene:**
- `locus_tag`, `aa_length`, `antismash_domains` (the domain call being checked)
- `blastp_top_def`, `blastp_accession`, `blastp_organism`, `pct_identity`, `query_coverage`, `evalue`, `bitscore`
- `agreement` — CONFIRM / REFINE / OVERTURN vs antiSMASH call (author-set from evidence)

The `agreement` column is the diagnostic value. `OVERTURN` entries require rewriting the corresponding gene interpretation in Mode B §4.

### Output file location
`<pkg>/bgc_blastp_panel/<BGC_ID>_online_blastp.csv` — also banked to the durable evidence store.

### How it enters Mode B cards
- **§4:** add `BLASTp top hit (org, %id, cov)` column beside the domain column; author prose from the *reconciled* call
- **§8:** state KCB anchor **with gene coverage**, then per-gene BLASTp verdict; if all hits are uncharacterised genus homologs, say "conserved in genus, no characterised product match"
- **§27:** resistance genes must be BLASTp-named (AAC(3), etc.), not left as generic Pfam
- **§28:** each BLASTp claim gets `observed (BLASTp nr, RID <id>, <date>)` as evidence type — the RID is the reproducibility handle
- **Strain taxonomy:** uniform consensus top-hit organism across all genes → genus inference, tagged `inferred` not `observed`

### Failure handling
- NCBI slow or FAILED → resubmit once; if still failing, author card from antiSMASH + KCB with explicit banner: "online BLASTp channel unavailable this session — domain calls are antiSMASH Pfam, unverified"
- No hit at threshold → record `no hit @ 1e-5`; for a core gene this is a novelty signal — flag, don't hide
- Network-restricted → channel is off; never fabricate hits

### Claim-safety (unchanged)
BLASTp hit = homology, not function or product identity. "Capacity consistent with," never "produces." A hit to a characterised protein is a hypothesis to test, not an assignment.

---

## Section 6: Bert Mode — Citation Verification Protocol

Source: `docs/BERT_MODE_PROTOCOL.md`. The citation discipline for every literature deliverable.

**Single rule:** accuracy over quantity. Never emit a citation that has not been verified against a primary source this session.

### When Bert Mode is active
- Any deliverable carrying citations (literature section, bench guide references, citation library, glossary addenda, manuscript reference list)
- User says "Bert Mode," "verify citations," "citation library," or "deep literature dive"
- Default-on for the §4.8 deliverable when network/PubMed access exists

### Verification standard

Every citation must be checked against PubMed, DOI.org, or the publisher page. A citation is VERIFIED only when ALL of the following are confirmed against the primary source in the current session: full author list, journal/year/volume(issue)/pages, DOI as a resolvable URL, PMID, PMCID where one exists, evidence type (Experimental/Review/Bioinformatic/Clinical).

If any field cannot be confirmed, the entry is downgraded — never guessed.

### Status tiers (four-tier standard)

| Tier | Meaning |
|---|---|
| Verified | Metadata resolved to a stable identifier and the summarized numbers were read from the paper's own full text this session |
| Partial | The record resolves but a wanted number or field couldn't be confirmed from available text; state exactly what's missing |
| Policy | A guideline, standard, or agency page rather than a primary study; note the "as of" date |
| GenBank | A sequence/assembly record rather than a paper; cite the accession |

### Anti-fabrication rules
- Never invent a PMID, DOI, PMCID, author list, or page range
- Never "reconstruct" a citation from memory and present it as verified
- If PubMed/DOI is unavailable, Bert Mode cannot reach Verified status — say so, mark the entry Partial, and record the exact search needed to close it
- Do not pad a reference list to hit a count. Three verified > ten unconfirmed.

### Verified reference bank (carry across all strains — no re-verification needed)

| Key | Citation | PMID | DOI |
|---|---|---|---|
| Chevrette2019 | Chevrette MG et al. Nat Commun. 2019. | 30705269 | 10.1038/s41467-019-08438-0 |
| Seipke2012 | Seipke RF et al. FEMS Microbiol Rev. 2012. | 22091965 | 10.1111/j.1574-6976.2011.00313.x |
| Ogawara2016 | Ogawara H. Molecules. 2016. | 27171072 | 10.3390/molecules21050605 |
| Wencewicz2019 | Wencewicz TA. J Mol Biol. 2019. | 31288031 | 10.1016/j.jmb.2019.06.033 |
| Yan2020 | Yan Y et al. Nat Prod Rep. 2020. | 31912842 | 10.1039/c9np00050j |
| Hegemann2020 | Hegemann JD, Suessmuth RD. RSC Chem Biol. 2020. | 34458752 | 10.1039/d0cb00073f |
| Li2021 | Li C et al. Front Bioeng Biotechnol. 2021. | 34395400 | 10.3389/fbioe.2021.692466 |
| Kramer2020 | Kramer J et al. Nat Rev Microbiol. 2020. | 31748738 | 10.1038/s41579-019-0284-4 |
| Cassat2013 | Cassat JE, Skaar EP. Cell Host Microbe. 2013. | 23684303 | 10.1016/j.chom.2013.04.010 |
| Risdian2019 | Risdian C et al. Microorganisms. 2019. | 31064143 | 10.3390/microorganisms7050124 |
| Johnson2008 | Johnson L. Mycol Res. 2008. | 18280720 | 10.1016/j.mycres.2007.11.012 |

---

## Section 7: Literature Search Protocol

Source: `docs/LITERATURE_SEARCH_PROTOCOL.md`. §8 of every strain analysis is deferred by default; this protocol is how you close the deferral.

**Why deferred:** Sapote runs without guaranteed network access. Protocol §4.8 requires every citation to carry a verified PMID and DOI — rather than fabricate, §8 is logged as `DEFERRED` with a completion path.

### Standard five-bucket search map

**Bucket 1 — Top antibacterial lead** (by BGC class):
- NRPS + β-lactamase-fold resistance: `nonribosomal peptide synthetase self-resistance beta-lactamase Streptomyces`
- T1PKS: `type I PKS Streptomyces antibacterial biosynthesis`
- Glycopeptide: `glycopeptide antibiotic biosynthesis gene cluster NRPS halogenase`
- Lanthipeptide class III: `class III lanthipeptide biosynthesis LanKC`

**Bucket 2 — Resistance/self-protection framing (every antibacterial lead):**
- Ogawara2016, Wencewicz2019, Yan2020 (all in verified bank above — reuse without re-verification)

**Bucket 3 — Top antifungal lead** (by BGC class):
- T1PKS polyene: `polyene macrolide polyketide Streptomyces antifungal biosynthesis`
- Lanthipeptide: Li2021 (in bank above)
- Nucleoside (nikkomycin/polyoxin): `nikkomycin polyoxin antifungal biosynthesis Streptomyces`
- HSAF/PTM: `HSAF dihydromaltophilin tetramate macrolactam antifungal sphingolipid`

**Bucket 4 — Ecology / habitat framing:**
- Bee/insect-associated: Chevrette2019 (in bank)
- Any Streptomyces: Seipke2012 (in bank)
- Strain-specific: `[Genus species] secondary metabolites`

**Bucket 5 — Strain-specific prior literature:**
Always: `[Genus species] secondary metabolites` and `[Genus species] biosynthesis antibiotic`. If hits exist, they become the first reference in §8.1. If no hits: "no prior secondary metabolite characterisation reported" is itself a positive novelty statement.

### Closing a §8 deferral

1. Run the searches for the specific BGC classes flagged in the Layer B §8 deferral note
2. Collect PMIDs (1–2 per topic bucket; reviews preferred)
3. Verify each DOI resolves at `https://doi.org/[DOI]`
4. Send PMIDs to Claude with the strain ID → §8 is written, workbook Literature_Index updated, package regenerated

Claude cannot resolve DOIs or PMIDs without network access. Citation verification is always a human step.

---

## Section 8: Claude ↔ ChatGPT Handoff Protocol

Source: `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md`. The structured handoff between the two LLM platforms.

**Platform roles:**
- **Claude (Sapote):** Judgment, scoring, ecology, literature, hallucination-trap audit. Writes C1–C4, D3, E1–E4, F1–F3, G1–G3.
- **ChatGPT (Mamey):** Extraction, assembly stats, RGGMCI computation. Writes A2 (assembly stats), A3, B1–B4, D1–D2.

The shared contract is the master workbook. Both platforms validate schema on receipt and log every write to H1_Handoff_Log before handing back.

### Automatic trigger conditions

Claude evaluates these at the end of every session where the workbook is modified:

| ID | Condition | Source sheet | Task emitted |
|---|---|---|---|
| T1 | ≥3 strains have `assembly_bp` = empty | A2_Strain_Registry | Task B: assembly stats CSV |
| T2 | ≥5 GOOD/MODERATE strains with `final_state = SCAN_SUMMARY_ONLY` | D1 + A2 | Task C: full RGGMCI packages |
| T3 | Any H2 gap with `assigned_platform = ChatGPT` and `status = OPEN` | H2_Gap_Queue | Mirror H2 gap as task |
| T4 | Any G2 row with `primary_role = type_strain_pending` | G2_Validation_Roles | Task A: new Mamey run |
| T5 | User requests "run more strains" or similar | — | Task A with recommended accessions |
| T6 | Batch merged, ≥2 known-chemistry type strains missing from G2 | G2 + benchmark table | Task A for next priority strains |

A brief is emitted BEFORE the CDSW next-paths list. Never mid-session — only at session end.

### Brief format
Named `CHATGPT_TASK_BRIEF_batchN_YYYY-MM-DD.md`. Self-contained (ChatGPT needs no additional context). Versioned (includes current workbook filename, strain count, BGC count). Closed-loop (ends with "Claude will merge automatically on receipt").

### ChatGPT return format
Single zip: `<project>_master_vN_after_batchN.xlsx` + `batchN_summary_vN.md` + `batchN_summary_vN.csv` + optional per-strain package zips. The master xlsx must have all existing strains intact plus new strains appended.

### Claude merge procedure (14 steps on receipt)

1. Read H3_Schema_Version — confirm ≤ current schema version
2. Filter new strains from `BGC_Master` (not already in B1)
3. Map columns to B1 schema
4. Apply heuristic ab_auto/af_auto/novelty_auto scoring (0–20 cap)
5. Build A2, B4, C1–C4, D1, F1, G2 rows
6. If RGGMCI FLBR grade = STRONG → add D3 entry
7. If strain has known chemistry → add G1 literature rows; assign G2 `benchmark_retrospective_validation` role
8. Update A1 (strain count, BGC count, last_updated)
9. Update A4 for new strains
10. Append A3 run manifest row
11. Append H1 handoff log row
12. Save as `SID-XXX_master_v1_0_Claude_filled_N+1.xlsx`

**Schema validation before any handoff (either direction):**
```bash
python mamey/workbook_schema_check.py path/to/workbook.xlsx
```
PASS required before handing off. Known gaps (empty B4 scan columns for benchmark strains) acceptable if documented in H2_Gap_Queue.

---

## Section 9: Deliverable Menu — Natural Language Triggers

Source: `docs/GUIDE/02_Quick_Guide.md`. Every phrase listed here is tested against actual pipeline behaviour.

### Getting started
- `"Can you work from this to get me the full deliverables?"` — the single most useful phrase; works from antiSMASH ZIP or sealed package; works mid-session to continue
- `"Run Mamey on [strain].zip and give me the full plate."`
- `"Run full Sapote analysis on [strain]."`

### Three evidence channels (run in this order for lead BGCs)
- `"Read the KCB front page for [strain]."` — named database leads with corroboration tier (STRONG/COINCIDENTAL/LARGE_GENERIC)
- `"BLASTp every gene in [BGC] and reconcile against antiSMASH."` — per-gene homology with CONFIRM/REFINE/OVERTURN, plus cluster coherence and function/novelty reads
- `"Plan a BLASTp round for [strain]."` — phased campaign plan for full BGC set

### Specific deliverables
- `"Triage board for [strain]."` / `"What are the top leads?"`
- `"Write me the layperson guide."` / `"Explain it to my PI."`
- `"Full Mode B for BGC028 (NODE_32 · region001)."` — always include node citation
- `"Locus maps for the top three leads."`
- `"BLASTP batches for BGC050."`
- `"Mode B for BGC028 plus a fermentation card and a wet lab matrix."` — combinations work

### Named deliverable bundles (CM codes from `docs/HOW_TO_USE.md`)
- `CM-2` or `"Discovery Brief"` — stat cards + key findings + compound-class table (default)
- `CM-3` or `"Bench Packet"` — compound-class + manuscript statement + isolation priority list
- `CM-5` or `"Ecology Set"` — full ecological synthesis package
- `CM-6` or `"Publication Packet"` — everything needed for writing up (default)
- `CM-7` or `"Full Spread"` or `"Give me everything"` — every single-strain layout
- `"Show output options"` — see the full §54 registry with all A1–A18, B, C, D layouts

### §21–§30 extension triggers
- `"Add the mass ladder for this RiPP BGC."` → §21
- `"Write the experimental decision tree for BGC028."` → §30
- `"I need the heterologous expression strategy."` → §23 (when MATURATION_GAP present)
- `"Give me the OSMAC protocol for [BGC]."` → §26
- `"What are the five most important open questions about this cluster?"` → §30

### Special review bucket triggers
- `"Nucleoside priority"` → review for antifungal relevance (nikkomycin/polyoxin-like)
- `"Flag all polyene/PTM/HSAF candidates"` → review for antifungal relevance
- `"Check all 'other' product rows"` → gene-level review required
- `"Show all RG-GMCI HIGH pairs"` → split-pathway reconstruction hypotheses

### Interpretive-priors and evidence-hardening deliverables (v9.7.338)
All report-only; every read is a class-level capacity hypothesis, judgment deferred, no structure/production/activity claim.
- `"Give me the good guesses for [strain]."` → `mamey good-guesses <root> --out <dir> [--docx] [--pdf]` — the single best claim-safe interpretive read per notable BGC, tagged `solid`/`rare`/`remarkable`/`notable`/`interesting`, each with a confidence band and the resolving experiment (`GOOD_GUESSES.md`/`.csv`/`.docx`/`.pdf`)
- `"Comparator coverage for [strain]."` → `mamey comparator-coverage <pkg>` — re-expresses every named MIBiG/KCB comparator against **two** denominators (matched/all-locus-genes and matched-core/all-defining-core) so a comparator carried only by transporters/regulators is exposed; the false-positive killer (`<STRAIN>_3b_comparator_coverage.csv`)
- `"Antifungal dossier."` → `mamey af-dossier <root> --out <dir> [--activity-table <csv>]` — AF lead board joined against an optional measured-*Candida* activity crosswalk (`AF_LEAD_DOSSIER.csv`/`.md`)
- `"Novelty shortlist."` → `mamey novelty-shortlist --package <pkg> --out <dir>` — strongest reference-dark / novelty-prior candidates (a prior, not proof)
- `"What's the realistic BGC count?"` → `mamey realistic-count <pkg>` — honest corrected denominator (fragments/primary-metabolism/duplicates netted out)
- `"Export the Mode B cards to Word/PDF."` → `mamey modeb-export --package <pkg> [--bgc <BGC_ID>] --out <dir>` → `.docx` + `.pdf`
- `"Domain reference sheet."` → `mamey domain-reference --package <pkg> --out <dir>` — KS/AT/KR/C/A/PCP… glossary + per-BGC ordered-domain readout for authoring §4/§5

### Cross-strain / cohort deliverables (v9.7.338)
- `"Cohort priority leads."` → `mamey cohort-leads --runs-dir <runs_gold> --out <dir>` → `PRIORITY_LEADS.csv` (one ranked lead board across every sealed run)
- `"Assemble the cohort master."` → `mamey cohort-assemble --runs-dir <runs_gold> --master <cohort_master.xlsx>` — build/refresh the cross-cohort master workbook from sealed gold runs
- `"Offline KCB locus map for [BGC]."` → `mamey figures kcb-locusmap --package <pkg> --bgc <BGC_ID> --out <png>` — query BGC vs its KCB/MIBiG comparator, zero network
- `"Would a master's student sign off on this tree?"` → `mamey signoff <tree.treefile>` (advisory analysis QC gate; also `tools/signoff_check.py`)

---

## Section 10: Calibration Corpus

Source: `docs/CALIBRATION_CORPUS_KNOWN_BGCS.md`. 15 known-compound reference BGCs for Mode B quality calibration.

**Purpose:** run gene-by-gene reads on known clusters; compare interpretation against published pathway; find where the read would have been wrong without literature access. The answer key exists for these clusters — it is the calibration.

| Accession | Compound | Class | Notes |
|---|---|---|---|
| BGC0000240 | lomaiviticin A | T2PKS diazo-fluorene | T2PKS aromatic thematic set |
| BGC0000245 | medermycin | T2PKS angucycline | T2PKS aromatic thematic set |
| BGC0000247 | mithramycin | T2PKS aureolic acid | T2PKS aromatic thematic set |
| BGC0000249 | nogalamycin | T2PKS anthracycline | T2PKS aromatic thematic set |
| BGC0000263 | ravidomycin | T2PKS benzo[a]naphthacenequinone | T2PKS aromatic thematic set |
| BGC0000264 | resistomycin | T2PKS pentangular polyphenol | T2PKS aromatic thematic set |
| BGC0000440/1 | teicoplanin | NRPS glycopeptide | Primary regression fixture |
| BGC0000243 | macrotetrolide (nonactin) | non-canonical PKS | 0 antiSMASH core genes — see note |
| BGC0002573 | phosphoramidon | peptidyl nucleotide | 1 core gene — minimal cluster |
| JN674503.1 / EU158805.1 | polyoxin | nucleoside antibiotic | Cross-accession consistency test |
| OR785474.1 | bafilomycin | T1PKS/saccharide macrolide | Hybrid PKS/NRPS macrolide |
| MT361594.1 | venturicidin | T1PKS/NRPS/saccharide | Hybrid PKS/NRPS macrolide |
| KP410250.1 | trioxacarcin A | PKS-like/T2PKS/betalactone/oligosaccharide | Complex hybrid |

**Edge cases this corpus tests:**

BGC0000243 (macrotetrolide) — 0 antiSMASH core genes despite being a real published pathway. Tests that low antiSMASH core-gene count does not mean low biosynthetic sophistication. The non-canonical assembly logic is not captured by standard PKS/NRPS rules.

BGC0002573 (phosphoramidon) — 1 core gene, 5 total genes. Same test from the minimal end.

The six T2PKS aromatic entries together test the "shared core, divergent tailoring" pattern. All share the minimal PKS (KSα/KSβ/ACP) core; tailoring determines product class. A scoring rule that incorrectly differentiates their core calls should fail this set.

The two polyoxin accessions (same compound, different genomic context) test cross-accession KCB consistency — a correctly-calibrated read should treat them as the same class with consistent core-gene logic.

---

## Section 11: Release Checklist Summary

Source: `docs/RELEASE_CHECKLIST_v9.md`. 7 gates, each with mandatory items. Summary:

**Gate 1 (Document sync):** One active controller; no stale term occurrences (`v8.1`, retired codename, `Davey`, `optional RG-GMCI`, `PENDING` in required fields, `Full Coverage Mode`); affiliation throughout; DELIVERABLE_CONTRACT consistent with CLAUDE_SYSTEM_PROMPT.

**Gate 2 (Prompt quality):** Both prompts mandate all deliverables without asking user; failure codes match across all docs; no aspirational behavior presented as available.

**Gate 3 (Schema verification):** WORKBOOK_SCHEMA.md matches produced workbook columns; scan_states.json schema matches what mamey_run.py emits; checkpoint CSV schema matches engine output.

**Gate 4 (CLI verification):** `mamey --help` matches HOW_TO_USE; `smoke/standard/gold` all documented and functional; failure codes match prompts.

**Gate 5 (Test matrix):** Six behavioral tests (see checklist for full list). Note: many are target/Release-2 acceptance tests, not yet implemented in the current suite.

**Gate 6 (Examples and references):** Test data present; layperson guide exemplar populated; CITATION.cff updated; CHANGELOG has a v9.7.241 entry.

**Gate 7 (Public readiness):** README accurate; RELEASE_MANIFEST.md has honest known limitations; SHA-256 checksums computed for all release files.

**Tier parity gates (added v9.7.6):** `tools/check_tier_parity.py` must pass for all four tiers before tag/push. Per-tier: registry present, build caches clean (0 `__pycache__`/`*.pyc`), pytest passes in-tier, leak audit clear (0 AS-strain IDs in public tiers), checksums self-verify.

**Multi-tier disclosure rule:** per-tier patch/verification status must be recorded at delivery. Never assume a fix propagated to all tiers — explicitly confirm and prominently flag if any fix landed in only some tiers.

---

## Section 12: The Bunny Hop Audit Game

Source: `docs/BUNNY_HOP_AUDIT_GAME.md`. Trigger: `"can we bunny hop?"` / `"run the bunny hop game"` / `"bunny hop [file]"`.

A random-sampling code audit protocol for the CODE tier. Purpose: spot-check implementation quality without systematic exhaustion of every line. Three phases:

**Roll:** randomly select 2–3 modules from the mamey/ directory (or accept the user's specified target)

**Audit:** Inspector role presents a finding with severity (Must-fix / High / Medium / Low), root cause, and evidence. Defender role challenges: is this a real bug, not a design decision? Was it already fixed? Does the evidence support Must-fix vs Medium?

**Consensus → patch card:** agreed findings enter a patch card (name, severity, affected file, line range, proposed fix, test needed). The patch card is input to a cut, never a cut itself.

The game produces audit findings suitable for a hostile reviewer, not a friendly collaborator. Findings from bunny hop runs are referenced throughout the ISSUES log and have been the source of several Must-fix patches (the dummy SHA256 fixture issue §3.1, the gene-mention regex §3.3, the missing f-string §3.2).

---

*Sources: `docs/HOW_TO_USE.md`, `docs/GUIDE/01_User_Manual.md`, `docs/GUIDE/02_Quick_Guide.md`, `docs/SINGLE_STRAIN_QUICKSTART.md`, `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md`, `docs/ONLINE_BLASTP_PROTOCOL.md`, `docs/BERT_MODE_PROTOCOL.md`, `docs/LITERATURE_SEARCH_PROTOCOL.md`, `docs/RELEASE_CHECKLIST_v9.md`, `docs/BUNNY_HOP_AUDIT_GAME.md`, `docs/CALIBRATION_CORPUS_KNOWN_BGCS.md`. Compiled 2026-07-09 · bundle v9.7.241.*

---

## Section 13: Annotated Live Pipeline Run — Teicoplanin Calibration Strain

*This section documents an actual pipeline run performed in this session on 2026-07-09 using the public MIBiG teicoplanin reference cluster (BGC0000440). All values are from real output files. This run demonstrates every key pipeline behavior in a known-answer context.*

### Input

**Strain:** BGC0000440 — *Actinoplanes teichomyceticus* (teicoplanin glycopeptide producer, MIBiG reference)
**Input file:** `tests/fixtures/micromonospora_humida_JAFEUC01.zip` (136 KB, public)
**Contents:** 98 files — `BGC0000440.region001.gbk` (317 KB, 53 CDS), `BGC0000440.gbk`, `BGC0000440.json`, `knownclusterblast/` directory, antiSMASH HTML viewer

**Why this strain:** teicoplanin is a publicly-characterised glycopeptide antibiotic with a known NRPS gene cluster. The VanHAX self-resistance genes, OxyA/B/C halogenases, and DpgABCD 3,5-dihydroxyphenylglycine (HPG) precursor pathway are all documented in the literature. Running this strain verifies that the engine correctly identifies the glycopeptide class, the T43-GPA trigger, and the VanHAX T1 self-resistance.

**Command run:**
```bash
python3 -m mamey run \
  --input-zip tests/fixtures/micromonospora_humida_JAFEUC01.zip \
  --strain BGC0000440 \
  --taxonomy "Actinoplanes teichomyceticus" \
  --source "MIBiG reference BGC; teicoplanin glycopeptide; public calibration strain" \
  --release PUBLIC \
  --mode gold \
  --json-evidence off \
  --outdir /tmp/teico_run/
```

**Wall time:** 18.8 seconds (extraction 4.4s, strain brief rendering 14.2s)

### Run output summary

**Assembly:** 89,713 bp · 1 contig · N50 89,713 bp · GC 71.97%

**BGC counts:** raw = 1 · interior = 0 · edge = 0 · full-contig = 1 · corrected = 0.25

**Assembly tier:** VERY_POOR (0.0% interior BGCs)

This is expected for a single-BGC reference cluster — the contig is the BGC itself, so it is Full-contig by definition. This correctly demonstrates the corrected-count discount: a single full-contig cluster counts as 0.25, not 1.0.

**Issues logged (both expected):**
1. `VERY_POOR assembly (0.0% interior BGCs)` — correct: this is a single-contig BGC fragment
2. `OVER_MERGE_CANDIDATES: 1 region carries ≥2 protoclusters` — the teicoplanin cluster contains 2 protoclusters (NRPS + PKS), correctly flagged by antiSMASH's own signal

### Triage board output (`BGC0000440_4_triage_board.csv`)

| Field | Value |
|---|---|
| BGC_ID | BGC001 |
| Contig | BGC0000440 |
| Products | NRPS; PKS; T3PKS |
| Boundary | Full-contig |
| Architecture grade | D (full-contig; likely truncated both ends) |
| Architecture capacity | glycopeptide |
| Class confidence | HIGH |
| AB score | 62.0 |
| AF score | 28.0 |
| Novelty | 23.0 |
| Lead tier | Medium |
| KCB top hit | BGC0000440.5 / Teicoplanin A2-1 through A2-5 |
| KCB cumulative | 58,408.0 |
| CCTT triggers | T43-GPA_glycopeptide, T43-HAL_halogenase |
| Corrected rank | 1 |
| AB recall | 91.5 |

**Score interpretation:** AB = 62.0 is driven by NRPS (+12) and glycopeptide keyword weights, capped by the Full-contig architecture grade D. The architecture-first assessment correctly identifies the glycopeptide chemotype (class confidence HIGH) from the 4 NRPS modules, halogenases, and VanHAX resistance signature — independently of the KCB anchor. The KCB anchor (BGC0000440 matching itself at 58,408 cumulative) is a self-hit from the MIBiG submission but is informative here as a calibration check.

### Scan states

All ten scans ran on the single BGC:

| Scan | Status | Key finding |
|---|---|---|
| KCB sweep | PASS | 1 region parsed; matched itself in MIBiG |
| RG-GMCI | NULL | 0 pairs (single-contig input; expected) |
| FLBR | PASS: STRONG | LMPKS_FRAGMENT_SET detected (4 NRPS modules are fragmented megasynthases) |
| CCTT | PASS | T43-HAL: 1 hit / 1 BGC; T43-GPA: 13 hits / 1 BGC |
| CGAD | NULL | No chitinase hits (expected for a glycopeptide cluster) |
| UMED | PASS | No maturation gaps (this is an NRPS, not a RiPP) |
| EFLS | NULL | 0 candidate pairs (single-contig) |
| Resistance | PASS | 3 total hits; 1 T1 BGC (VanHAX) |
| bldA/TTA | PASS | 1 BGC assessed; T4 (no bldA found in single-contig) |
| TFBS | PASS | 1 motif hit: GBL_AdpA_like |

**Key calibration checks:**
- T43-GPA fired 13 times (OxyA, OxyB, OxyC, DpgS, the HPG aminotransferases, glycosyltransferases — all correct for a glycopeptide)
- VanHAX resistance correctly assigned T1 (class-concordant: VanH, VanA, VanX are the classic glycopeptide self-resistance triad)
- FLBR STRONG is correct — the 4 NRPS genes (CAE53350–53353) are the megasynthase core

### Resistance scan detail (from workbook `Resistance_SelfProtection` sheet)

| Resistance family | Count |
|---|---|
| Beta_lactamase_fold | 0 |
| Erm_methylase | 0 |
| VanHAX_like | **3** |
| APH_AAC | 0 |
| Fosfomycin | 0 |
| Self_resistance_general | 0 |

VanH (CAE53343), VanA (CAE53344), VanX (CAE53345) — three genes, correctly identified, correctly assigned T1. This is the canonical glycopeptide self-resistance triad.

### Figure outputs (26 total)

The `render-all-figures` command ran 5 figure modules, producing 26 figures:
- **Root (14 figures):** _8a through _8m landscape, composition, DAPR scatter, AB ranked, AF ranked, funnel, class distribution, CCTT map, length histogram, edge composition, novelty ranked, KCB anchors, genome atlas
- **Domain level (3):** domain-level Mode B enrichment figures
- **Figures rendered (2):** additional render-module outputs
- **Gold figures (2):** cohort-mode F-series (limited at N=1 strain)
- **Locus maps (2):** `BGC001_BGC0000440_locus.png` and `.svg` — the gene-arrow diagram showing all 53 CDS

### Workflow gate status (W0–W10)

After extraction, the `sapote_workflow.py` reports:
- W0–W2 PASS (sealed, triage, DAPR boards)
- W3 PENDING — Mode B templates not yet emitted
- W4–W10 BLOCKED (pending W3)

Next action required: `mamey emit-modeb-template --package <pkg> --bgc BGC001` to emit the §1–§30 skeleton, then author and verify the card.

### Validation receipt

```
file_presence: PASS
checksum_integrity: PASS
rggmci_gate: PASS (NULL — no pairs expected at N=1)
gold_completeness: JUDGMENT_PENDING
status: MAMEY_COMPLETE
```

The package is complete and sealed. `MAMEY_COMPLETE` means extraction is done and all checksums are verified. `JUDGMENT_PENDING` means Mode B cards have not yet been authored — the standard state after extraction before Sapote judgment begins.

### What the locus map shows

The BGC001 locus map (SVG + PNG) displays all 53 CDS as gene arrows across the 89.7 kb contig. Reading left to right from position 0:
- Positions 0–15 kb: regulatory flanking genes (AraC regulator, TetR regulator, short-chain dehydrogenase, murF-like, VanH/A/X triad)
- Positions 20–47 kb: NRPS core (4 large genes CAE53350–53353, totalling 9,069 aa; CAE53352 alone is 4,067 aa — the largest single gene)
- Positions 48–65 kb: tailoring (MbtH chaperones, mannosyltransferase, ABC transporter, OxyA/B/C halogenases)
- Positions 65–82 kb: HPG/DHPG precursor biosynthesis (DpgABCD, HpgT, HmaS, Hmo, AroA-type, StrR/LuxR/AfsR regulators)
- Position 83 kb: thioesterase (canonical TE release domain)

---

## Section 14: Standard Operating Procedures Summary

Source: `docs/SOPs/` directory, 15 SOPs (3 placeholders, 12 complete). Master index: `SOP_MASTER_INDEX.md`.

### SOP-00: Start Here / Choosing the Right Path

**Input classification decision tree:**
1. AntiSMASH ZIP with many regions → the staged path is `mamey doctor` → `mamey inspect <zip>` → `mamey run --mode gold` (gold is the only analysis mode)
2. AntiSMASH ZIP with one region → inspect + interpret warnings carefully (single-region = reference BGC or test, not full genome)
3. Sealed Mamey package → `mamey validate <pkg>` (do not re-run)
4. BLASTp Hit Table CSV → `mamey blastp-followup --hit-table <csv>` (do not re-run Mamey)
5. BLASTp XML2 → pair with hit table when possible
6. Patch packet ZIP → read README/manifest/diffs before applying

**Required first statement before running any command:** "This appears to be [raw antiSMASH output / a sealed Mamey package / BLASTp result output / a patch handoff packet]."

### SOP-13: Claim Boundary and Evidence Language

**Evidence → claim mapping:**

| Evidence type | Supports | Does NOT support alone |
|---|---|---|
| antiSMASH class | BGC class hypothesis | Exact compound identity |
| KnownClusterBlast | Similarity to known BGC | Purified product claim |
| BLASTp hit | Gene-function support | Product identity |
| RG-GMCI | Split/neighbourhood inference | Chemical detection |
| Resistance / transporters | Self-protection context | Activity claim |
| Literature | Plausibility / precedent | Activity in THIS strain |
| LC-MS/MS | Metabolite evidence | Gene function unless linked |
| Purified compound | Compound identity/activity | Genome-wide mechanism |

**Acceptable language:** "supports a BGC class call," "resembles a known biosynthetic neighbourhood," "contains homologs of," "is a priority for follow-up," "candidate antimicrobial lead," "claim-safe evidence suggests."

**Prohibited language without orthogonal evidence:** "produces compound X," "is compound X," "confirmed antifungal/antibacterial," "this BGC makes," "definitive product identity."

### SOP-15: Cross-Chat Merge and Patch Handoff

Another chat can join an active session by reading these files in order:
1. `handoff/START_HERE_FOR_OTHER_CHATS.md`
2. `SOP_MASTER_INDEX.md`
3. `bug_hunt/SOP_DERIVED_BUGHUNT_MATRIX.csv`
4. `cut_plan/NEXT_CUT_PLAN.md`
5. Then the SOP relevant to its task

This is the operational form of the multi-chat architecture. The reading order is fixed because later files reference concepts defined in earlier ones.

---

## Section 15: Canonical Glossary Extended — Key Terms from GLOSSARY.md

Source: `docs/GLOSSARY.md` (767 lines). This section captures entries from the bundle's own canonical glossary not covered in the comprehensive_glossary document. Structured entries follow the GLOSSARY.md format exactly.

**Evidence axes and lead classes (five-axis model):**
- Mode B verdict = CONFIRM: weight +3
- SARP present (per-BGC): weight +2
- KCB-anchored: weight +1
- Tier-1 diagnostic: weight +1
- DasR site: weight +0.5

Class A = CONFIRM + SARP. Class B = one strong axis only. Class C = KCB or weaker support. Canonical Class-A count in the project: 12 (6 SID + 6 AS). Earlier "17" and "6" predated banked AS verdicts.

**Regulatory elements (TFBS scan):**
- SARP — Streptomyces Antibiotic Regulatory Protein. Pathway-specific activator. Per-BGC presence is one of the five evidence axes (weight +2). Strongest candidate evidence that a lead is an actively-regulated antibiotic pathway.
- DasR — GlcNAc-responsive global repressor. Links chitin breakdown products to antibiotic onset. Weight +0.5 (a fractional point).
- AdpA/GBL — A-factor/γ-butyrolactone cascade. The quorum-sensing developmental switch; governs timing of secondary metabolism.
- BldD — Master developmental repressor. Gatekeeps the growth-to-sporulation/secondary-metabolism switch.
- PhoP — Phosphate-response regulator. Couples phosphate limitation to antibiotic production; relevant to media design.

**Evidence tags:**
- `[EG]` — evidence-grounded but not literature-verified (provisional)
- `[VL]` — verified against literature

**Plain-language overloaded words (selected):**
- Kernel — the Slim Judgment Kernel: the condensed instruction core driving Sapote's behaviour
- Monolith — the single large parent-controller document; wins over everything except the Deliverable Contract
- Manifest — two senses: (1) `manifest.json` handoff object that Mamey emits; (2) the release manifest listing shipped files
- Board — a results table (Lead Board, Hive Board, Triage Board)
- Floor — a minimum a score cannot drop below; a Tier-1 diagnostic floors a BGC's priority score
- Ceiling — a maximum a claim cannot exceed
- Guard — an audit-finding check that fails the build if a known defect reappears
- Contract — the Deliverable Contract; outranks the monolith
- Register — the missingness register (records what's absent) and the output registry (lists produced deliverables)

**Failure / status codes:**

| Code | Meaning |
|---|---|
| INPUT_MISSING | Required input file not present |
| MAMEY_FAILED | Deterministic scan failed; reason required |
| UNSUPPORTED_ACCESSION_MODE | Must supply antiSMASH ZIP, not accession |
| ANTISMASH_PARSE_FAILED | antiSMASH output could not be parsed |
| WORKBOOK_SCHEMA_CONFLICT | Workbook columns do not match required schema |
| PACKAGE_QA_FAILED | Package manifest, checksums, or required files missing |
| RECOVERY_NEEDED | Partial output exists; exact recovery inputs listed |
| DEFERRED | Item intentionally deferred; reason and completion path required |
| MAMEY_COMPLETE | Package passed all extraction gates; ready for Sapote judgment |
| MAMEY_COMPLETE_WITH_ISSUES | Core valid, peripheral issues logged |
| JUDGMENT_PENDING | Extraction complete; Mode B cards not yet authored |

**Ecological habitats:**
- Attine / fungus-garden — fungus-growing ants and associated actinomycetes (e.g. *Pseudonocardia*, *Amycolatopsis*); classic defensive-symbiosis source of antifungals
- Bryophyte / lichen — mosses, liverworts, and lichens and their associated actinomycetes
- Hymenoptera / bee — bees and wasps and their symbionts; the third habitat set
- Fungus-growing termite — *Macrotermes* system; independent cross-system comparator to attine ants

---

*Teicoplanin run conducted 2026-07-09 · BGC0000440 · 53 CDS · 89.7 kb · 18.8 s wall time · 26 figures · MAMEY_COMPLETE · v9.7.241 / engine 1.9.111*

*Last updated: 2026-07-09 · v3 additions (Sections 13–15: live run, SOPs, glossary extension) · Bundle v9.7.319*

---

## Section 16: Mode B Card Verification — The Presentation Gate (v9.7.246)

Before any Mode B card leaves a session, it must be verified against a **sealed package**. Verifying against the card alone cannot catch the class of defect that v9.7.246 exists to prevent.

### The command

```bash
mamey verify-modeb --package <sealed_pkg> --bgc BGC001
mamey verify-modeb --package <sealed_pkg> --bgc BGC001 --interp   # v9.7.338: also run the interpretation/judgment gate (WARN-only)
```

**§4 evidence gate now bites (MB-01, v9.7.338).** When the strain carries a BLASTp panel, §4 asserting a `CONFIRM/REFINE/OVERTURN` verdict without the reconciled per-gene closest-match table (or with no authoritative package core count reaching the gate) now raises an `EVIDENCE_GAP` / `COVERAGE_UNVERIFIED` **WARN** — where the pre-fix gate was effectively dead on every card from the supported workflow. The summary can read `OK (§4 coverage NOT verified — no package core count)`; re-run with `--package … --bgc …` so the real-core-count coverage actually gates. WARN-level, never a structural refuse.

**`--interp` (v9.7.338)** adds the Mode-B interpretation/judgment gate on top of structure + depth: it flags a card that asserts a class read without at least one alternative interpretation, a resolving experiment, or capacity-level (not production) framing. WARN-only — it advises the author, it never blocks a seal.

`--package` is not optional in practice. `authored_verify` uses it to load `known_loci` from `<pkg>/*_cds_table.csv`, which is what `PHANTOM_LOCUS` needs to answer its question: *does every `ctgN_M` cited in this card exist in this strain?* **Without a CDS table the lint is silent** — so a card verified without a package passes a check that never ran.

### Reading the output

`verify-modeb` reports a `readiness_state`. Only one value may be presented.

| State | Cause | Action |
|---|---|---|
| `DRAFT` | Any ERROR finding, or the card is a STUB / depth-unverified | Fix the ERROR; re-author thin sections |
| `VERIFIED` | Depth adequate, but a blocking correctness code fired | Resolve the contradiction; do not present |
| `RELEASE_READY` | Depth adequate, no blocking code | May be presented |

The four blocking codes are `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`, `FACT_MISMATCH`, and `PHANTOM_LOCUS`. Each is a correctness failure, not a style failure. A card that is structurally complete, adequately deep, and claim-safe can still be held at `VERIFIED`.

### If `PHANTOM_LOCUS` fires

The card cites a locus tag that does not exist in this strain's CDS table. The finding names up to six of them.

**Delete the paragraph. Do not reword it.** There is no BLASTp result to reword — the observation was never made about this organism. Rewording produces a hedged fabrication, which is worse than an unhedged one because it reads as careful.

Check two things:
1. **Templated boilerplate** carried over from a different strain's session. This is the v9.7.246 case: 74 cards inherited a real *Amycolatopsis* result from the §4 template.
2. **A copy-paste from an example card.** Example cards are written about real strains and contain real loci.

### Remediating the 74 known cards

Cards authored before v9.7.246 carry the templated §4 and §16 text. They are **not repaired by the fix.**

```bash
# For each affected card:
mamey verify-modeb --package <sealed_pkg> --bgc <BGC_ID>
# → PHANTOM_LOCUS ERROR, readiness_state: DRAFT
```

Delete every §4 and §16 paragraph containing `ctg12_71`. Then re-run `verify-modeb`. If per-gene BLASTp evidence is genuinely wanted for that BGC, produce it — offline-preferred as of v9.7.260: if you already have NCBI results, `mamey ingest-blastp --hit-table <hits.csv> [--xml <aln.xml>] --package <pkg>` (zero network); otherwise `mamey blastp-online --package <pkg> --bgc <BGC_ID>` — then author §4 from the real result.

### If `LOCUS_BGC_MISMATCH` fires (v9.7.256)

The card cites a **real** locus, but under a BGC it does not belong to — the finding names the locus and its true home BGC. This is the AS-XXX BGC006/BGC010 class: templated boilerplate carried a real gene into another BGC's card. Move the observation to the correct BGC's card, or delete it if it was never made about the cited BGC. Do not simply relabel the BGC id without checking the gene's real membership.

### If `PANEL_ABSENT_CLAIM` fires (v9.7.256)

The card states a per-gene BLASTp result for a BGC that has **no BLASTp panel** in this package. Either the panel was never built for that BGC (build it and run the channel, then author from the real result) or the claim is a fabrication (delete it). Note the residual gap: the lint keys on the panel *selection*, not on returned alignments, so a per-gene claim on a BGC that has a selection but was never actually run will **not** trip it — that case is on the author's discipline until the lint is extended to require a results artifact.

---

## Section 17: Pre-Release Gate Sequence (v9.7.246)

Two gates were added to the release path in v9.7.243. The full sequence, in order:

```bash
# 1. Environment and bundle integrity
python3 -m mamey doctor
python3 tools/sync_version.py --check              # → engine 1.9.111, bundle 9.7.246

# 2. Documentation anchors
python3 tools/check_monolith_freshness.py          # exit 1 on stale anchor or retired doctrine
python3 tools/check_dangling_refs.py --strict-paths # path-qualified reference ratchet
python3 tools/gen_marker_catalog.py --check        # catalog in sync with source_scans.py

# 3. Fast pre-validation
python3 tools/run_chatgpt_surrogate_gate.py        # 22 pytest files, ~13s

# 4. Full suite
python3 -m pytest -q                               # 2884 passed / 152 skipped / 0 failed

# 5. Tier parity (before tag/push)
python3 tools/check_tier_parity.py

# 6. Zip hygiene
python3 tools/preflight_zip_hygiene.py <release.zip>
```

**Live receipts on bundle v9.7.246 (this session):**

```
check_monolith_freshness: PASS
  monolith: vetted v9.7.242 | live v9.7.246 | drift 4 patches | 450,214 chars
  (anchor honest, no retired doctrine)

surrogate gate: PASS (22 pytest files, 13.4s step-sum)

full suite: 2884 passed, 152 skipped, 2 warnings in 262.98s (0:04:22)
```

**Note on `check_monolith_freshness`.** It does not demand that the monolith be re-read. It demands that the monolith state, truthfully, how far behind it is. A drift of 4 patches with an honest anchor passes. A drift of 185 patches with an anchor claiming a recent read-through — the v9.7.242 state — fails.

---

## Section 18: Auditing the Source Tree — the Bunny Hop workflow

The audit protocol described in Section 12 now has a tool behind it.

### Step 1 — Generate the roll pool

```bash
python3 tools/file_atlas.py --out docs/FILE_ATLAS.csv --md docs/FILE_ATLAS.md
python3 tools/file_atlas.py --orphans
```

Live output on v9.7.246: **35 orphan candidates of 280 files.** An orphan is a module that nothing imports, that no CLI verb reaches, and that no test names. This is exactly the population from which the "defined and never invoked" defect class is drawn (Development Issues Compendium, Group 14).

### Step 2 — Or roll on fan-in instead

`docs/FILE_ATLAS.md` opens with **Highest fan-in (change these carefully)**. On v9.7.246: `tools/_wbio.py` (38 importers), `mamey/models.py` (13), `mamey/crosswalk.py` (11).

Both `_wbio.py` and `crosswalk.py` were hardened immediately after the atlas surfaced them, and both carried real defects — permission widening on a `0600` deliverable in a bundle that ships a MERGED-PRIVATE tier; a latent `ValueError` in a function called by eleven modules. **Fan-in is where a latent defect propagates furthest. Roll there when the orphan list is exhausted.**

### Step 3 — Reproduce before fixing

Every v9.7.243–246 fix was reproduced against the real artifact before the patch was written. The changelog is explicit about this, and the failures it catalogues are all failures of proxy verification:

- The `kcb-frontpage` filter passed CI for thirteen cuts because the test **stubbed `bgc_id`** into the hit dicts. The real `regions.js` has no such key.
- The `tab-reconcile` region bug survived because the reference fixture sits on a **single-region contig**, where `areas[0]` is always right.
- The P7a overlay truncation was signed off because the test exercised **one BGC and one round** — a shape that cannot expose a truncate-on-second-write bug.

**Reproduce on the real artifact. A passing test on a fixture that cannot fail is not evidence.**

### Step 4 — Ask what question each existing gate asks

The v9.7.246 fabrication passed claim-safety, evidence-presence, citation, and padding. Each asked a real question. **None asked whether the cited gene existed.** When adding a gate, write down the question it answers, then check whether any existing gate already answers it. If the set collectively leaves a question unasked, that is the gate to build.

---

*Last updated: 2026-07-09 · v4 additions (Sections 16–18: card verification, release gates, Bunny Hop workflow) · Bundle v9.7.246*
