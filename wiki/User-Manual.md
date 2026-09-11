# The Sapote–Mamey User Manual

*Operating guide for the Sapote–Mamey genome-mining pipeline · current to bundle v9.7.428 / engine Mamey 1.9.163*
*· 2026-06-29*

> This Manual tells you **how to run** Sapote–Mamey and **how to read what it gives you**, front to back in the order you actually use it. For *why each part exists and how it relates to the rest*, see the **Encyclopedia** (cross-referenced as → §Vol.Chapter). The Manual is operational; the Encyclopedia is the deep reference behind it. One **Glossary** ([`GLOSSARY.md`](../docs/GLOSSARY.md), with its **Core concepts** section for the load-bearing terms) is the single source for term definitions — this Manual and the Encyclopedia both point to it rather than redefining terms.

---

## 1 · What Sapote–Mamey is

Sapote–Mamey is a **two-layer genome-mining pipeline** for actinomycete (and, increasingly, fungal) natural-product discovery. It is not an environment you work inside; it is a tool you run *on* genomes.

1. **Mamey** is the software: a deterministic Python engine (the `mamey` package). It parses antiSMASH output, builds the BGC inventory, runs the scans, computes the corrected count, and emits the triage board, manifest, briefs, and figures. *Deterministic* means same input → byte-identical output, held by the test suite (the full suite at v9.7.401 (engine 1.9.143)).
2. **Sapote** is the judgment layer: a structured LLM prompt system that applies **claim-safe interpretation** on top of Mamey's deterministic facts. It writes the Mode B narrative, pathway hypotheses, and claim-safety audits.

Mamey is the factual floor; Sapote is the interpretive ceiling; the contract between them keeps "what the data says" from blurring into "what we think it means." → Encyclopedia Vol I, Vol III.

**Internalise this before anything else:** every claim the pipeline makes is *capacity-level*. It reports "biosynthetic capacity consistent with class X," never "produces compound Y." A KCB hit is **similarity, not identity**. Bioactivity metadata is optional strain-level context, never pinned to one BGC without governed linkage, and absence of recorded metadata is **never** read as "inactive." → §I.3.

**A note on durability (important).** Mamey's deterministic outputs persist automatically. Sapote's *judgment* — the Mode B cards — does not, unless you commit it back through the receipt path (§4.4). A Mode B card that lives only in a chat window is lost when the session ends; it must be ingested into the package's judgment store to become part of the durable, citable record and to reconcile into the cohort workbook. This is the single most common way analysis work goes missing; §4.4 is how you prevent it.

## 2 · Setup and installation

Mamey parses antiSMASH output; it does not run genome detection itself.
*(engine 1.9.143, bundle v9.7.401)*

### 2.1 · What you need

**Python 3.10 or later.** Python 3.12 is recommended — it matches the compiled wheels distributed with the bundle. Check with `python3 --version`.

**The bundle ZIP.** Unzip `sapote-mamey-v9.7.148-CODE-20260629.zip` anywhere on your machine. All commands run from inside that directory.

```bash
unzip sapote-mamey-v9.7.148-CODE-20260629.zip
cd sapote-mamey-v9.7.148-CODE-20260629
```

**antiSMASH output for your genome**, as the `.zip` antiSMASH emits — region GenBank files plus the run JSON. Mamey reads three JSON modes: `off` (default, fastest), `bounded` (enables RiQ scores and A-domain specificities), `full` (richest active-site data). Start with `off` or `bounded`.

### 2.2 · Install the engine

```bash
pip install -e .
```

On a managed system Python (Debian/Ubuntu) that rejects this with "externally-managed-environment":

```bash
pip install -e . --break-system-packages
```

On Miniconda (the standard): plain `pip install -e .` works without the override.

This installs the `mamey` command and the two core dependencies (`openpyxl` for workbooks; `ijson` is vendored inside the bundle so it works offline automatically).

### 2.3 · Install the add-on wheels

The pipeline's heavier dependencies (the Gemini comparison stack, the offline HMM engine, and the
figure-rendering libraries) ship **separately** from the lean Sapote–Mamey bundle, as an add-on of
vendored wheels. Keeping them out of the bundle means every pipeline cut stays small and loads fast.

**The add-on can arrive in any shape — the installer accepts them all.** Because a single large zip
uploads slowly, the add-on is split so the parts load in parallel:

| Add-on part | Size | Contains | Needed for |
|---|---|---|---|
| `sapote-addons-core` | ~27 MB | pyhmmer, pyskani, biopython, pyrodigal, pyfamsa, … | **Everything except figures** — starts runs, BLASTp, HMM, ANI, Gemini |
| `gemini-figures-part1/2/3` | ~24–34 MB each | scipy, numpy, pandas, matplotlib, logomaker, pycirclize + the 148-family HMM | `mamey figures` (atlas, ANI heatmap, sequence logos) and the extended HMM scan |

Load the **core** part alone to start analysing immediately; add the **figure** parts when you need
figures. You can attach them as separate zips, as one combined zip, or as loose `.whl` files — the
installer scans every add-on location, pools whatever wheels it finds, and installs them:

```bash
bash bundle_support/install_sapote_addons.sh            # auto-discovers every attached add-on part
bash bundle_support/install_sapote_addons.sh /path/to/wheels   # or point it at an explicit directory
```

Core dependencies are required and verified; figure dependencies are best-effort — if the figure
parts were not attached this session, the installer says so and the pipeline runs fully without them
(only `mamey figures` is unavailable). The 25 most important HMM models ship in the bundle itself, so
HMM scanning and adjudication work with the core add-on alone; the 148-family set in the figure part
is an enhancement.

**Biopython filename note.** The wheel filename must use dots, not underscores, in the version and
platform tags. If your file transfer replaced dots with underscores, rename it before installing:

```
# rejected:  biopython-1_87-cp312-cp312-manylinux2014_x86_64_manylinux_2_17...whl
# correct:   biopython-1.87-cp312-cp312-manylinux2014_x86_64.manylinux_2_17...whl
```

The wheel contents are unchanged — only the filename needs restoring.

### 2.4 · The right bundle tier

The release ships in four tiers — same engine, different data exposure:

| Tier | Use for |
|---|---|
| **CODE** | Internal working tier — full engine + analysis tools |
| **CODE-analysis-free** | Engine only, no analysis extras |
| **SID-public** | Shareable tier — unpublished AS-strain identifiers stripped |
| **MERGED-PRIVATE-scaffold** | Cross-strain merge scaffold — PRIVATE by construction |

Use CODE for all internal analysis. Never distribute MERGED-PRIVATE.

### 2.5 · Verify the install

```bash
mamey doctor                          # pre-flight check: Python, deps, permissions, bundle integrity
python3 tools/sync_version.py --check # should report `engine 1.9.143, bundle 9.7.401`
python3 -m pytest -q                  # green suite = tier is intact (requires pytest wheel)
```

The startup banner on every run also prints a dependency line:

```
deps: openpyxl✓ | ijson(vendored)✓ JSON streaming on | figures✓ | biopython—(optional; shim in use)
```

If a required dependency shows ✗, install it from the wheels folder before running.

→ Full dependency reference and system binary install (pandoc, xelatex): `docs/PREREQUISITES.md`.

## 3 · Running a strain

The run command has the shape:

```
PYTHONPATH=$PWD python3 -m mamey run \
  --input-zip <antiSMASH_output.zip> \
  --strain <ID> \
  --display "<Genus species strain ID>" \
  --taxonomy "<Genus species>" \
  --source "<provenance>" \
  --release <PUBLIC|PRIVATE> \
  --mode <standard|gold> \
  --json-evidence <off|bounded|full> \
  --outdir <dir>
```

Key flags (→ Encyclopedia §VII.7 for the full tunable surface):
- `--release` — **PUBLIC** vs **PRIVATE**. Hard guard: `AS-###` / `AJS` / `PENDING` strains are unpublished → **PRIVATE**; `SID` / `WW-` and named/accession genomes are **PUBLIC**. Any merged set containing AS data is PRIVATE.
- `--mode` — analysis depth. `gold` additionally emits the gene-by-gene Mode B layer so the deep-dive runs from the package (→ §4, → Encyclopedia §VI.5).
- `--json-evidence bounded` — enables the region-mapped **RiQ** layer (streams large JSONs; RiQ is exempt from the record cap). `full` carries the richest active-site/substrate data.
- `--source` — provenance string. **Provide it** — when absent, habitat falls to `ENGINE_DEFAULT_PLACEHOLDER`, and isolation-source is a weak proxy for function regardless (never over-interpret it into an ecological claim).

**What a clean run looks like.** The console reports cohort resolution (the resolver files a strain by its organism string, e.g. a `SID-XXX` label → cohort SID; a non-actinomycete ends with a loud `*** NON-ACTINOMYCETE` warning — exclude, don't score), then a status line. The terminal status vocabulary (v9.7.83+) is one of:
- `MAMEY_COMPLETE` — clean run.
- `MAMEY_COMPLETE_WITH_ISSUES` — completed, but the manifest carries `[ISSUE]` lines worth reading (MULTIBATCH, VERY_POOR assembly, PHO_CLUSTER, E-signal, etc.).
- `VALIDATION_FAIL` — the package did not pass its integrity gate; do not use it.

**The package naming convention.** The sealed package is named after the **bundle** version with the engine version as a provenance suffix: `<strain>_SapoteMamey_v9.7.100_engine1.9.98_Complete_Package.zip`. (Before v9.7.85 it used only the engine version, which made the producing bundle unidentifiable from the filename.)

**Where the outputs land.** Inside `runs/<ID>/package/`: the numbered deliverables (`_1_…` intake through the triage board `_4_triage_board.csv` and the dedicated `_4c_AB_lead_board.csv` / `_4c_AF_lead_board.csv`), the `_5_workbook.xlsx`, the `AntiSMASH_Evidence_Parse.json`, the judgment register, and — in gold mode — the gene-by-gene deep layer. `OPEN_ME_FIRST.html` is the entry point; `START_HERE.md` is the reading order; `manifest.json` is the authoritative file inventory; `run_phase_receipts.jsonl` records per-phase START/DONE receipts; `checksums_sha256.txt` seals it.

**Previewing a raw antiSMASH ZIP before running:**
- `mamey inspect <antiSMASH.zip>` — one-screen preview of what Mamey sees in a **raw antiSMASH output ZIP** before running (positional; not a sealed-package reader — a sealed `*_Complete_Package.zip` is rejected).

**Inspecting a sealed package without re-running** (v9.7.83+ read-only commands):
- `mamey explain <package_dir>` — narrative walkthrough of what's inside the sealed package and what to do next (positional package directory).
- `mamey list-bgcs <package_dir> [--axis rank|ab|af] [--top N] [--json]` — BGC inventory from the triage board (positional package directory; `--axis` default `rank`). `--json` emits `bgc_id, contig, node_id, products, boundary, ab_score, af_score, novelty_auto, cctt_triggers, lead_tier, kcb_top, …`.

## 4 · Reading the output

This is the chapter most users live in. The pipeline emits a triage board, a DAPR priority table, Mode B cards, and figures. → Encyclopedia §VI.4, §VI.5.

### 4.1 · Reading a DAPR row

DAPR (dual antibacterial/antifungal priority ranking) ranks leads on both axes. Read a row left to right:

- **Rank** — order on the axis after all guards. Means *read this first*, not *confirmed*.
- **Region** — always `BGC## | contig | region##`. A bare BGC id is unciteable. → §4.5 on why the anchor matters.
- **Boundary** — Interior (trusted) / Edge (possibly truncated) / Full-contig (completeness unknowable). **As of v9.7.85 boundary status no longer lowers the score** — it lowers *confidence* (architecture grade) only. See §4.6.
- **AB / AF** — the headline axes; Exceptional ≥85 / High ≥70 / Medium ≥50 are assigned from `max(AB, AF, novelty)`. Below 50, **Low** means a resolved non-allow-listed class token is present; **Inventory** means all resolved classes are on the governed Inventory allow-list, or the region is unresolved. These are routing priors, not activity calls.
- **KCB** — rendered as a band with "(similarity)". Capacity consistent with the class, never an identification.
- **CCTT** — a corroborated class trigger is *why* a region ranks above a keyword-only one.
- **Mobile flag** — an ICE-dominated, non-class-typed region is **excluded**, with its reason.

**Read the excluded list too** — it is where the engine shows its work (why a region a raw score would rank is absent).

### 4.2 · Reading a Mode B card

Mode B is the per-BGC dossier. The finished card is **§1–§48** (`FINISHED_FULL48_CURRENT_EVIDENCE`, gate-enforced since v9.7.369); **§1–§20** is the always-required core subset (never a finished card on its own) and **§1–§30** is the legacy candidate/calibration profile. Every section has a job:

- **§1 Identity and node/region** — BGC id, contig, region, boundary (Interior / Edge / Full-contig). Always cite the node alongside the BGC id; a bare BGC number is unciteable.
- **§3 Boundary and assembly status** — fragmentation caveats; boundary (Interior / Edge / Full-contig); UMED/FLBR/RGGMCI flags; what is likely off-contig.
- **§4 Gene-by-gene interpretation** — the parsed per-gene/domain evidence; the enzymatic basis for the class label.
- **§5 Core biosynthetic logic** — how the core enzymes assemble the scaffold; connects domain architecture to structural consequences.
- **§8 Comparator/KCB interpretation** — what the nearest database hit tells you (class anchor) and what it cannot tell you (structure, identity).
- **§9 Alternative hypotheses** — each alternative weighed against evidence, not just listed; which is most parsimonious and why.
- **§11 Product-family interpretation** — tailoring complement connected to scaffold complexity implications.
- **§12 Bee/microbe ecological interpretation** — host context, mechanism, literature anchor, confidence tag.
- **§19 Final verdict** — evidence summary → alternative rejection → claim ceiling (positive/negative pair) → confidence tags.
- **§28 Evidence provenance ledger** — claim-by-claim source tracing (observed/computed/inferred/assumed). Required for all completed cards.
- **§30 Experimental decision tree** — five open questions → resolution experiments → programme consequences. Required for all completed cards.

**Interpretive floor (v9.7.146+):** §5 must connect domain architecture to structural consequences, not just name domains. §9 must weigh alternatives with evidence. §12 must name the ecological mechanism, not just the ecological context. §19 must argue the verdict, not restate §11. See `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`.

**Edge/FC BGCs (v9.7.147+):** boundary status is a metadata flag, not a visibility suppressor. All detected BGCs appear in the triage board sorted by score. Edge and full-contig BGCs in POOR/VERY_POOR assemblies receive full Mode B depth with boundary caveat in §3 and §19 only.

A card's job is to make the evidence trail visible enough that a wrong call cannot hide. → §VI.5 for a full worked card.

### 4.2a · The three-channel evidence workflow (v9.7.176–182)

A Mode B lead card is now built on three independent evidence channels, not one. This exists
because of a caught-in-the-wild failure — BGC006 (AS-XXX) was anchored to *colibrimycin* on a
KnownClusterBlast score of 3734, when colibrimycin actually shared only a handful of genes with the
query. A high score is not cluster identity. The fix was to stop relying on any single inherited
signal and reconcile three:

1. **KCB front page — the named lead, with its coverage.** `mamey kcb-frontpage <antismash_dir>`
   reads the "Most similar known cluster" column and reports it with a corroboration tier from
   *both* similarity% and matching-gene count: **STRONG** (a real cluster's worth of shared genes),
   **COINCIDENTAL** (high similarity but one or two genes — a fluke, demoted), **LARGE_GENERIC**
   (many generic genes at trivial similarity). The rule the card now enforces: never state a KCB
   anchor without its gene coverage.

2. **Online BLASTp — independent per-gene homology.** `mamey blastp-online --package <gbk> --bgc
   <ID>` submits each gene to NCBI, reconciles the top hit against the antiSMASH domain call
   (CONFIRM / REFINE / OVERTURN), and resolves strain taxonomy from the consensus organism. On
   BGC006 this overturned two annotations (a "β-lactamase" that is really an esterase; a "phenol
   hydroxylase" that is a ferritin) and placed the strain in *Amycolatopsis*. The channel is
   **fail-closed**: if NCBI is unreachable it says so and fabricates nothing. It needs biopython
   (the `bio` extra, or the add-on, which vendors it).

3. **HMM adjudication — the intrinsic tie-breaker.** When BLASTp disagrees with antiSMASH,
   `mamey hmm-adjudicate <region.gbk> --locus <lt>` settles it on the domain signature
   (SUPPORTS_BLASTP / SUPPORTS_ANTISMASH / AMBIGUOUS / INSUFFICIENT) — offline and deterministic.
   HMM also supplies the module grammar (KS→AT→DH→KR→ACP order and module count) that BLASTp cannot
   resolve, and rescues short/orphan genes (RiPP precursors) that get no BLASTp hit.

The division of labour is durable: **HMM tells you what the machine is** (intrinsic domain
architecture, offline, deterministic); **BLASTp tells you whose machine it is most like and whether
the product is known** (extrinsic identity, organism, novelty). The emitted §1–§30 template seeds
§4 and §8 so this order is the path of least resistance, not a rule to remember.

**Function and novelty.** The BLASTp channel also reports two things a discovery pipeline cares
about, kept as separate axes: **gene-level novelty** (how divergent each gene is from anything
sequenced) and **product-level novelty** (whether the whole cluster matches a characterised
compound). These do not move together — BGC006 is gene-*conserved* (its genes are ~83% identical to
known *Amycolatopsis* proteins) yet product-*novel* (no characterised compound matches at cluster
level). "Conserved genes, unknown product" is the honest and more valuable read than a weak MIBiG
name. See `docs/ONLINE_BLASTP_PROTOCOL.md` for the full spec and the BGC006 worked example.

### 4.3 · The standing deliverables

Beyond the boards and cards, a run/cohort produces: the **BGC inventory** (serial then class-grouped, node/contig on every row); the **workflow status** overview (per-strain progress arrows Parse→Scans→RG-GMCI→Boards→ModeB→Banked); **Run Observations** (fixed-shape reflection, every claim tagged observed/computed/inferred/assumed); and the **cross-strain synthesis** (per-strain capacity + genus layer + a leak-clean PUBLIC cut when the cohort is PRIVATE).

### 4.3a · Post-seal deliverable subcommands (v9.7.338)

v9.7.338 adds twelve on-demand subcommands that consume an **already-sealed package** (or a directory of them) and emit an extra deliverable. Like `render-figures` / `cohort-figures` / `ingest-receipts`, they are **post-seal and non-blocking** — they read facts the engine already computed and **never re-run the engine, move a score, or touch a published tier**. Everything they emit is capacity-level and judgment-deferred (sign-off gated); the last four are advisory helpers. Run them from the bundle root against a sealed `…/package` directory (or a runs dir):

**Cross-strain ledgers**
- **`cohort-leads`** — union every sealed triage board into ONE ranked cross-strain priority-leads CSV (Exceptional+High leads); carries a MIXED-ENGINE caution when strains span engine versions. *Non-scoring re-projection.*
  `python mamey_run.py cohort-leads --runs-dir <runs_dir> [--out COHORT_PRIORITY_LEADS.csv]`
- **`cohort-assemble`** — assemble many sealed packages into a cross-cohort master table (`COHORT_MASTER.csv` + siblings, optional `--xlsx`). *Non-scoring.*
  `python mamey_run.py cohort-assemble --runs-dir <runs_dir> [--out COHORT_MASTER.csv] [--xlsx]`

**Evidence / false-positive layer**
- **`comparator-coverage`** — the two-denominator MIBiG comparator-coverage evidence layer: a named-MIBiG-family "lead" that survives only one of the two coverage denominators is exposed as low-specificity rather than surfaced. The false-positive killer. *Report-only, non-scoring* (its scoring wire is a future, sign-off-gated change and is NOT active).
  `python mamey_run.py comparator-coverage <package> [--cohort-runs-dir <runs_dir>]`

**Antifungal + interpretive deliverables**
- **`af-dossier`** — the Antifungal Lead Dossier: one row per AF-lead BGC, joining BGC capacity (class-level routing prior) against **optional** measured Candida activity (strain-level context). Capacity and measured columns are kept in separate groups so they never mix; it runs with no wet-lab input, emitting "no measured data" when the crosswalk is absent. *Report-only, non-scoring.*
  `python mamey_run.py af-dossier <root> [--out DIR] [--activity-table CSV] [--depth N]`
- **`good-guesses`** — the claim-safe interpretive-priors deliverable (md / csv / docx / pdf): the single best claim-safe read per notable BGC, tagged **solid / rare / remarkable / notable / interesting**, each carrying its confidence and the experiment that would resolve it. Every page carries the claim-safety footer. *Report-only, non-scoring.*
  `python mamey_run.py good-guesses <root> [--out DIR] [--pdf] [--docx] [--depth N]`

**Document + figure export**
- **`modeb-export`** — export an authored Mode B card (`.md`, or a package `mode_b/` directory for batch) to Word `.docx` + `.pdf` (reportlab; the DOCX path degrades gracefully if `python-docx` is absent). *Non-scoring.*
  `python mamey_run.py modeb-export <card.md|mode_b/> [--outdir DIR] [--format docx|pdf|both]`
- **`figures kcb-locusmap`** — an offline KnownClusterBlast comparative gene-cluster locus map (PNG + SVG + `data.csv`) from a sealed input ZIP or an extracted knownclusterblast txt; degrades to a clear message (never a traceback) with no matplotlib. *Non-scoring figure.*
  `python -m mamey.kcb_locusmap --zip <zip> --contig <NODE> --out-dir <dir> --strain-id <ID> --bgc-id BGC### [--products "..."] [--top-n 6]`

**Count / novelty / reference (advisory)**
- **`domain-reference`** — emit the bundled Mode-B domain functional-context reference dictionary from sealed package(s).
  `python mamey_run.py domain-reference --package <pkg> [--out FILE]`
- **`realistic-count`** — an honest corrected-denominator BGC count (marginal-drop + HIGH RG-GMCI merge) beside the raw region count.
  `python mamey_run.py realistic-count --package <pkg> [--out FILE]`
- **`novelty-shortlist`** — a composite multi-signal novelty shortlist (KCB-dark + low recognizability + RG-GMCI + cohort-unique domain).
  `python mamey_run.py novelty-shortlist --package <pkg> [--top 30] [--out FILE]`

**Analysis QC + Mode-B interpretation gates**
- **`signoff`** — the "would a master's student sign off?" analysis QC gate (§8-style checks mechanised): objective checks on Newick trees — outgroup sanity, contaminant/label-cruft, support/thin-tree. Advisory; always exits 0.
  `python mamey_run.py signoff [tree.treefile ...] [--minutes N]`
- **`verify-modeb --interp`** — adds the Mode-B **interpretation** (judgment-substance) layer to `verify-modeb`: **WARN-only** `INTERP_*` findings (`INTERP_NO_SYNTHESIS`, `INTERP_NO_TIER`, `INTERP_REFDARK_SILENT`) reading the §4 synthesis/ref-dark prose. It only *adds* warnings — the structure gate's PASS/FAIL verdict and exit code are unchanged, so a card can be structurally green and still show interp warnings. For an authoring loop that should FAIL on missing judgment, run the standalone gate `python -m mamey.modeb_interp_gate <card.md> [--strict]`.
  `python mamey_run.py verify-modeb --package <pkg> --bgc BGC### --interp [--interp-strict]`

### 4.4 · Persisting Mode B judgment — the receipt path (v9.7.85)

**This is the step that keeps analysis from being lost.** When Sapote produces Mode B cards, they must be written back into the package's judgment store, or they exist only in chat. The flow:

1. The Sapote session ends a Mode B batch by emitting one **`mode_b_receipt.json`**:
   ```json
   {
     "schema_version": "mode-b-receipt-1.0",
     "strain_id": "AS-XXX",
     "session_id": "sapote_2026-06-19_AF",
     "cards": [
       {"bgc_id": "BGC018", "mode_b_md": "…full §1–§48 markdown…",
        "layperson_paragraph": "…", "fermentation_note": "…"}
     ]
   }
   ```
2. Ingest it:
   ```
   mamey ingest-receipts --package runs/AS-XXX/package \
     --receipt mode_b_receipt.json \
     --master cohort/master_workbook.xlsx
   ```

This writes each card's `.md` into the package, flips the judgment register row to `COMPLETE`, and — with `--master` — reconciles the workbook's `E1_Mode_B_Index` so the cohort tracker shows real per-BGC completion with `report_file` links. It is **fail-closed** (an unknown `bgc_id` is reported and skipped, never invented) and **idempotent** (re-ingesting does not duplicate rows). → Encyclopedia §VI.8.

**Banking a strain into a cohort.** After a run (and after Mode B ingest), the strain's data accrues into the master workbook via the `--master` update pass; the first bank establishes the cohort schema and every later source must match it — which is how the engine normalizes before it appends, rather than naively concatenating divergent schemas.

## 5 · Configuration

The pipeline's behavior is tuned through **named module constants**, not scattered magic numbers (→ Encyclopedia §VII.7 for the full file:line table):

1. **Calibration weights** — keyword tables, `DIAGNOSTIC_BONUS` (how *strongly* a signal scores).
2. **Geometric thresholds** — tier cutoffs (85/70/50), assembly bands (70/45/20), the flanks (5000/10000/300) (*where the lines are drawn*). **Note:** the edge/full-contig score penalty was removed in v9.7.85 (§9) and is no longer a tunable threshold.
3. **Guard sets** — diagnostic-trigger / floor-exclusion / over-call lists (*which signals are load-bearing*).
4. **Run options** — `--release`, `--mode`, `--json-evidence` (one run, not the calibration).

**Workflow for any change:** edit the named constant → run the suite → re-run a reference strain to see exactly what moved. A calibration you cannot see move is one you cannot trust. Re-weighting a keyword is reversible calibration; adding a class to a diagnostic-trigger set is a *guard-set* change and deserves more scrutiny. **Any change to a scoring constant breaks cross-strain comparability** — strains scored under the old constant must be re-scored before they are compared to strains scored under the new one (the engine version is how you track which is which).

## 6 · How the engine works (module by module)

This section is the bridge to the Encyclopedia: enough of the internals to read the output critically. → Encyclopedia Vol II–VII for the full treatment.

- **Parsing & the data model** (`parsers.py`, `antismash_evidence.py`). Two streams: BioPython parses the region GenBank into `BGCRecord` / `CDSFeature` / `DomainFeature` (this is where product-class labels come from); a JSON stream (via `ijson`) plus GBK `/sec_met_domain` extraction yields the diagnostic evidence (Pfam hits, NRPS/PKS consensus, RiPP cores, KCB hits). **Mamey reads what antiSMASH already computed — it never re-runs detection.** → §II.
- **Geometry & counting.** Boundary status (Interior / Edge / Full-contig) is computed from span vs contig length; it drives the **corrected count** (Interior 1.0 + Edge 0.5 + Full-contig 0.25) and the architecture confidence grade. → §III, → Glossary "Edge status".
- **The scans** (`source_scans.py`). The 88-marker registry plus the **CCTT / T43** class-trigger framework run as regex over the *parsed* objects (not the raw ZIP). A corroborated T43 trigger is what lets a region floor to Medium and earn the diagnostic bonus. The supporting scans (resistance, transporter, chitinase/CGAD, TFBS, regulator) inform judgment. → §VII, → Glossary.
- **Reconstruction (RG-GMCI).** Homology-guided shared-reference linkage across contigs — it proposes that two fragments on different contigs are one split pathway when they share MIBiG references. **It does not join contigs at the nucleotide level**, and its bonus is routing priority, not claim confidence; promiscuous-hub and distant-reference pairs are down-weighted. **As of v9.7.100 the rescue layer was reworked** to use the full ClusterBlast evidence rather than KnownClusterBlast alone: hits are now tagged by database of origin (`db_kind` — knownclusterblast vs clusterblast vs the excluded subclusterblast), each pair records a `rescue_evidence_base` (BOTH_KCB_AND_CB / CLUSTERBLAST_ONLY / KNOWNCLUSTERBLAST_ONLY — so a novel cluster with genome neighbours but no characterized match is no longer invisible), a `functional_rescue_class` cross-checks gene-role complementarity (core vs tailoring split = real split; both-core = paralog), and a **terminus-truncation rescue** flags the simplest split of all — an Edge region ending *at* its contig terminus paired with a small severed-arm contig — overriding a paralogy verdict that rests on a gene legitimately multi-copy within one cluster. All of these remain candidate inference, not contig joining. → §VIII, → Glossary "RG-GMCI rescue layer".
- **Scoring & judgment-support** (`scoring.py`). Three axes (AB / AF / novelty), each a base floor + class-keyword credit + a gated diagnostic bonus, modulated by the guard stack (primary-metabolism / mobile-element / mis-anchor suppression; standing-rule downgrades; RiPP-fragment floor) and RG-GMCI rescue. Tier = max axis. → §IX, and §9 below for the v9.7.85 scoring change.
- **Compound-class annotation** (`compound_class.py`, v9.7.86). A deterministic layer that records the chemotype a BGC's own evidence is consistent with (anthracycline, polyene macrolide, tetracycline, glycopeptide, phenazine, …), read from antiSMASH's own `t2pks.product_classes` prediction and the resolved MIBiG product line (own-evidence only; never the raw KCB anchor blob). It carries a `confidence` field (HIGH / MODERATE / LOW) and a `cytotoxic_flag`. Most chemotypes are **annotation-only** (recorded, no score impact); three well-anchored families carry a scored consequence (polyene-macrolide → AF, ionophore → AB, anthracycline → its own cytotoxic category). Surfaced in the manifest and Mode B §5.

### 6.5 · The fifteen cassette families and the scans (ten core + two context)

Every cassette family in your workbook `Cassette_Registry` sheet and every scan that emits a sheet is documented in the generated catalog, which is regenerated from the scanner so it cannot drift from the code:

→ **`docs/USER_CATALOG.generated.md`** (cassette catalog + scan catalog; build-checked via `tools/gen_user_catalog.py --check`).

The **ten core deterministic scans** are the genome-wide pre-triage layer — KCB, RG-GMCI, FLBR, CCTT, CGAD, UMED, EFLS, Resistance, bldA/TTA, TFBS (→ Concepts Q&A Bank 35). Two further **context scans**, `regulators` and `transporters`, emit their own workbook sheets but are read as context rather than triage drivers — which is why "the scans" is sometimes quoted as ten and sometimes as twelve; both are right once you separate core from context.

Reading reminders carried from the catalog: a cassette count is **capacity / signal, not product or activity**; absence of a family is **not** a negative call; `siderophore_metallophore` and `transporter_resistance` are widespread and low-discrimination.

## 7 · Running fungal and cyanobacterial genomes

Sapote–Mamey is designed and calibrated for **actinomycete bacteria**. Fungal and cyanobacterial antiSMASH outputs run through Mamey without engine changes, but several interpretation-layer assumptions do not carry across kingdoms. The worked fungal reference is *Capronia epimyces* CBS 606.96 → Encyclopedia Volume IX.

### 7.1 · What transfers across kingdoms

The **structural/geometric layer is taxon-agnostic**: BGC parsing and inventory, boundary classification and the corrected count, assembly tiering, KCB/MIBiG similarity anchoring (MIBiG 4.0 includes fungal clusters), RG-GMCI geometry, package sealing, and claim-safety language all work unchanged. On the *C. epimyces* pilot the engine extracted 25 BGCs (corrected 24.5, GOOD assembly) and sealed cleanly. The structure is correct; the interpretation needs manual review below.

### 7.2 · What does not transfer — three interpretation failures

1. **The CCTT framework is mostly silent.** The T43 families encode actinomycete biology; fungi build chemistry differently. On *C. epimyces* only T43-PHO fired (correctly — PEP-mutase means the same thing in both kingdoms). The other 24 BGCs fell to Inventory because the bacterial detector cannot *see* fungal chemistry — **these are under-calls, not genuine negatives.** Manual gene-by-gene Sapote review is required for any fungal BGC of interest.
2. **bldA/TTA and TFBS scans are not applicable.** bldA/TTA is actinomycete-specific; TFBS keys on bacterial regulator motifs. Both produce numbers on a fungal genome that are meaningless. As of v9.7.86 the engine marks bldA/TTA **NOT_APPLICABLE automatically** on non-actinomycetes (keyed on organism actino-status, not on TTA presence — so a GC-poor non-actinomycete no longer gets a false T4 report); still treat TFBS output as NOT_APPLICABLE by hand.
3. **The CGAD chitinase scan inverts — a claim-safety hazard.** In an actinomycete, high GH18/GH19 chitinase + AA10 LPMO counts suggest fungal-cell-wall degradation (antifungal-relevant). In a fungus, GH18 chitinases are *housekeeping* enzymes for the organism's own cell wall. CGAD on a fungal genome returns high counts that, under the bacterial framework, contribute false antifungal signal. **Reinterpret all fungal CGAD output as "cell-wall chitin metabolism (self)"; do not route it into antifungal claims.** (T43-NUC, chitin-*synthase* inhibition, is mechanistically distinct and may still apply.)

### 7.3 · Running a fungal genome — required manual steps

Use the standard command (there is no `--kingdom` flag yet; the fungal patches P-F1–P-F6 are unimplemented → §IX.6). After the run, before reading output: (1) **discard the automated lead tiers** (bacterial-framework under-calls — use corrected count + assembly tier only); (2) **null the bldA/TTA section**; (3) **null the TFBS section**; (4) **re-read all CGAD output as self cell-wall biology**; (5) **run a manual gene-by-gene Sapote pass** for BGCs of interest (key fungal signatures: iterative KS, PT domain for NR-PKS, scytalone dehydratase for DHN-melanin, TRI5 for sesquiterpenoids, DMATS for indole alkaloids); (6) **T43-PHO may be trusted**; (7) **KCB similarity to fungal MIBiG is trustworthy** at capacity level.

### 7.4 · Cyanobacterial genomes

Processed in bacterial mode; structural handling identical. Caveats milder than fungal: T43-PHO transfers; T43-NUC may partially apply; RiPP triggers apply only with gene-level confirmation. bldA/TTA is NOT_APPLICABLE. TFBS motifs likely don't apply (treat as preliminary). CGAD does not invert (cyanobacteria aren't chitin-walled) but read it ecologically, not mechanistically. Corrected count, assembly tier, KCB, and RG-GMCI all apply normally. MIBiG-visible classes include cyanopeptolins, microcystins (flag hepatotoxicity), anabaenopeptins, cryptophycins, and RiPPs.

### 7.5 · Roadmap to full cross-kingdom support

A six-patch roadmap (P-F1–P-F6 → §IX.6): P-F1 adds a `--kingdom` flag (reads the antiSMASH taxon label, records kingdom in the manifest, threads it through the scan pack); later patches gate actinomycete-only scans, fix the CGAD inversion, and add a fungal CCTT subset. Until they ship, the §7.3 manual steps are the correct procedure. Anyone implementing fungal extensions should fork the SID-public tier and verify a reference actinomycete run remains byte-identical before/after.

## 8 · Type strain reference analyses

Full analyses for public type strains are in Encyclopedia Volume XII, each BGC cited with contig + antiSMASH region (e.g. BGC057 (CP023690.1 · region057)) so reports are reproducible across detection settings:
- ***Streptomyces spectabilis* ATCC 27465** (CP023690.1): primary calibration reference; 67 BGCs all Interior; spectinomycin BGC057 at Medium with the BGC0000715.5 anchor.
- ***Streptomyces liangshanensis*** (CP050177.1): 45 BGCs all Interior; HSAF-class antifungal BGC026 at AF 67.0 (T43-PTM); azoxy N–N BGC027 (T43-NN).

→ Encyclopedia Volume XII for complete Mode B, layperson guides, bench guides, and ecological synthesis.

## 9 · Recent scoring & reconstruction changes

### 9.1 · v9.7.84 — edge/full-contig penalty removed

**As of engine 1.9.85 (bundle v9.7.84), the edge/full-contig fragmentation penalty is neutralized to zero.** Previously a BGC on a contig edge lost score (Edge −3.5, Full-contig −6.3 on the AB/AF axes); now boundary status does not deduct from the score at all.

**Why.** An audit across the AS cohort found Edge/FC BGCs show *no truncation signature* in their base score (mean base AB was equivalent across Interior / Edge / Full-contig), so the penalty was a flat pessimism prior, not a correction for missing genes. Yet at the Medium threshold it was decisive — it flipped most near-threshold edge leads into Inventory, burying exactly the overlooked fragments the pipeline exists to surface in fragmented genomes.

**What replaced it.** Truncation uncertainty is real and still recorded — as a **confidence** signal, not a score deduction. An Edge/FC region drops to architecture grade C/D and carries its boundary status in the rationale, so a reader sees "extent unconfirmed" without the lead being demoted below complete-but-trivial clusters. Boundary status still drives the **corrected count** (Interior 1.0 / Edge 0.5 / Full-contig 0.25) — that is unchanged.

→ See the *AB/AF Scoring Methods* document §4.7 and the selvamicin walkthrough (BGC0001773) for the full rationale and a worked case.

### 9.2 · v9.7.100 — RG-GMCI contig-rescue overhaul

**As of engine 1.9.98 (bundle v9.7.100), the RG-GMCI rescue layer reads the full ClusterBlast evidence rather than KnownClusterBlast alone**, and gains a physical (coordinate-based) rescue path. The ranked-pairs output (`*_4A_RGGMCI_ranked_pairs.csv`) carries new fields:

- **`db_kind` / CB–KCB separation.** Each shared-reference hit is tagged by source database — knownclusterblast (characterized MIBiG cluster), clusterblast (cross-genome GenBank neighbour), or the excluded subclusterblast (sub-operon). Earlier code blind-merged all three.
- **`rescue_evidence_base`.** BOTH_KCB_AND_CB / CLUSTERBLAST_ONLY / KNOWNCLUSTERBLAST_ONLY — so a novel cluster with real genome neighbours but no characterized match is no longer invisible to a KCB-only path.
- **`functional_rescue_class`.** Cross-checks gene-role complementarity (core vs tailoring split = real split; both-core = paralog) by core-fraction asymmetry.
- **Terminus-truncation rescue (`TERMINUS_TRUNCATION_SPLIT`).** The simplest split of all — an Edge region ending *at* its contig terminus, paired with a small severed-arm contig — overriding a paralogy verdict that rests on a gene legitimately multi-copy within one cluster.

All remain **candidate inference, not nucleotide-level contig joining**. → §6 (RG-GMCI bullet), → Glossary "RG-GMCI rescue layer", → Encyclopedia §IV.4.

### 9.3 · Comparability

Scores are **not comparable across an engine boundary** without a re-score. The boundaries to date:

- **1.9.84 → 1.9.85** — the edge/full-contig penalty removal (§9.1).
- **1.9.85 → 1.9.86** — the v9.7.85 KCB-anchor keyword-contamination fix.
- **1.9.96 → 1.9.97** — data-driven RiPP extraction (v9.7.99): RiPP families beyond the original four are no longer dropped, so any strain carrying a ranthipeptide / linaridin / thioamitide / other extra RiPP family changes; original-four-only strains are byte-identical.
- **1.9.97 → 1.9.98** — the RG-GMCI contig-rescue overhaul (v9.7.100): new ranked-pair fields and two new package artifacts. This changes rescue *routing* and adds fields but does **not** alter the AB/AF/novelty base scores, so it is the mildest of the four — but it is still an engine boundary for cohort-pooling purposes.

A cohort "re-scored to the current engine" must be re-scored under **1.9.98** specifically — the genus bank is pinned at 1.9.96 and is therefore *two* boundaries behind, so its `assert_comparable_with` will refuse to pool it with a 1.9.98 cohort until it is re-scored. **Re-score any cohort under the current engine (1.9.98) before cross-strain comparison.**

---

## 10 · Figure generation

This chapter is the single reference for every figure Sapote–Mamey produces: what it shows, whether it renders by default or on demand, how to trigger it, and where it lands. Two principles hold across all of them:

1. **Every figure is a data-only PNG with a companion `_data.csv`.** The PNG is for the eye; the CSV is the figure's data, so a figure can always be re-plotted or audited without re-running the pipeline. Strain names display as *Genus species* strain `<ID>`.
2. **Every figure carries a claim-safe footer.** Capacity-level, not a product claim; KCB = similarity, not identity; gene roles are antiSMASH rule/smCOG annotations, not BLASTP-confirmed. Figures never assert compound identity.

Figures fall into three groups: **default per-strain** (rendered automatically in every run), **default cohort** (rendered when you build the cohort atlas), and **optional/on-demand** (rendered when you ask for them, in-run or post-seal).

### 10.1 · Default per-strain figures (every run)

These render automatically during a standard or gold run, into the package's `figures/` directory, and are listed in `figures/figure_manifest.csv`.

1. **DAPR scatter** (`<strain>_dapr_scatter.png`) — the diagnostic landscape: every BGC placed by antibacterial vs antifungal capacity, sized/annotated by priority. The at-a-glance "what does this strain's biosynthetic potential look like" figure.
2. **Antibacterial lead board** (`<strain>_ab_ranked.png`) — top BGCs ranked by AB capacity score, node/contig-anchored.
3. **Antifungal lead board** (`<strain>_af_ranked.png`) — the same for AF capacity.
4. **Funnel** (`<strain>_funnel.png`) — raw BGC count → corrected count → lead set, showing how fragmentation and standing-rule downgrades reduce the candidate pool.
5. **AB/AF vertical panels** (`<strain>_ab_af_panels.png`) — stacked AB and AF lead boards for side-by-side reading.

### 10.2 · Default per-strain locus maps (every run)

Deterministic gene-arrow maps render automatically in-run into the package's `locus_maps/` directory, catalogued in `locus_maps/locus_map_manifest.csv`. Each gene is an arrow drawn to bp scale, strand-aware, colored by its functional role (PepM, Ppd, NRPS module, PKS module, RiPP machinery, transport, regulation, …) from `mamey/data/locus_role_palette.json`; unrecognized genes are grey "other / hypothetical". Three triggers fire automatically:

6. **Top-lead locus maps** (`<BGC>_<node>_locus.png`) — a single-BGC map for the top antibacterial lead and the top antifungal lead.
7. **Mode B locus maps** (`<BGC>_<node>_locus.png`) — one map per Mode B BGC (gold mode is uniform full depth for every BGC).
8. **RG-GMCI HIGH pair maps** (`<BGC_a>__<BGC_b>_pair_locus.png`) — a paired, stacked two-panel map for each RG-GMCI HIGH pair, for split-cluster / homology review. Renders only when HIGH pairs exist (it depends on the RG-GMCI HIGH set being counted correctly).

The map's role labels come from the full antiSMASH `gene_functions` annotation. Because that blob is now sealed into the gene context, the same maps can be re-rendered post-seal (§10.5).

### 10.3 · Default cohort figures (the master atlas)

Rendered when you build the Bee–Wasp Master Figure Atlas from a populated cohort workbook (the master `.xlsx`). These are cohort-level, not per-strain.

9. **Master dashboard** (`fig_master_dashboard`) — the cohort overview panel.
10. **Dual-priority atlas** (`fig_dual_priority_atlas`) — AB and AF priorities across the whole cohort.
11. **BGC assembly landscape** (`fig_bgc_assembly_landscape`) — BGC yield against assembly quality per strain (the "is low yield real or a fragmentation artifact" figure).
12. **Special-bucket heatmap** (`fig_special_bucket_heatmap`) — special-review burden by strain (nucleoside priority, polyene/PTM flags, other-token rows, RG-GMCI high pairs).
13. **Top lead boards** (`fig_top_lead_boards`) — cohort-wide top antibacterial and antifungal leads.
14. **Strain card atlas** (`fig_strain_card_atlas`) — a per-strain summary card grid.

### 10.4 · Optional / on-demand figures

These are not rendered automatically; you invoke them with `render-figures --figure-set <name>` (post-seal, against a sealed package or a cohort workbook). All are non-blocking — a render failure writes a skip card and never invalidates the package.

**Domain-level figure pack** — `render-figures --package <pkg> --figure-set domain-level` (runs domain-level first if its tables are absent; add `--source-antismash <zip>` for full per-domain detail). Lands in `domain_level/figures/`:

15. **Role-burden heatmap** (`domain_role_burden_heatmap.png`) — top BGCs × controlled domain-role categories, cell = domain count. Where biosynthetic complexity concentrates.
16. **Core biosynthetic burden** (`core_biosynthetic_domain_burden.png`) — per-BGC stacked bar splitting biosynthetic-core domains from accessory clutter. The architecture-confidence axis, separate from AB/AF.
17. **Per-BGC domain strips** (`<Strain>_<BGC>_domain_strip.png`) — node-first domain arrows for each top lead, colored by domain role, collapsing very large BGCs with a receipt.

**Cohort class-capacity heatmap** — `render-figures --figure-set cohort-class --workbook <cohort.xlsx>`. One figure:

18. **Class-capacity heatmap** (`cohort_class_heatmap.png`) — strain × primary-biosynthetic-class matrix, cell = BGC count, viridis. Applies the standing permanent-exclusion rule: **saccharide and NAPAA are dropped from the class comparison** (and the footer says so). All-zero class columns are dropped to keep it legible.

**Cross-strain figure suite** — `tools/build_cross_strain_figures.py --rg-dir <rggmci_dir> --out-dir <dir>`. A bundle of cohort comparison figures (class prevalence, fragmentation gradients, raw-vs-corrected BGC, genome-size-vs-BGC, and related), each with its data CSV. See the figure prompt specs under `prompts/figure_prompts/cohort/`.

### 10.5 · Re-rendering figures post-seal

Because the deterministic core seals before figures render (the Finding-L sidecar contract), and because figures live outside the core checksum set, you can re-render any optional figure set from a sealed package without re-running the pipeline:

- `render-figures --figure-set standard` — the per-strain lead/diagnostic figures.
- `render-figures --figure-set locus-maps` — re-renders the gene-arrow maps from the sealed per-CDS gene context (the K0 path). Gene roles are reconstructed from the sealed `gene_functions` blob, so role assignment matches the in-run maps. Note: the in-run maps read the region GBK directly and the post-seal maps read the overlap-keyed gene context, so the *set* of CDS shown for a given BGC can differ slightly between the two; both are honest views of the same region.
- `render-figures --figure-set domain-level` — the domain figure pack.
- `render-figures --figure-set cohort-class --workbook <xlsx>` — the cohort class heatmap.

### 10.6 · Where figures live (quick map)

| Figure group | Directory | Trigger |
|---|---|---|
| Per-strain leads/diagnostics (1–5) | `figures/` | automatic, every run |
| Per-strain locus maps (6–8) | `locus_maps/` | automatic, every run |
| Cohort master atlas (9–14) | atlas output dir | build the master atlas |
| Domain-level pack (15–17) | `domain_level/figures/` | `--figure-set domain-level` |
| Cohort class heatmap (18) | chosen out dir | `--figure-set cohort-class` |
| Cross-strain suite | chosen out dir | `tools/build_cross_strain_figures.py` |

Every figure in every group ships a companion `_data.csv` and is registered in a figure manifest for its group.

---

*Sapote–Mamey User Manual · current to bundle v9.7.428 / engine Mamey 1.9.163 Consolidates the former 01_User_Guide.md and 01_User_Manual.html into one task-flow-first operating manual; deep internals live in the Encyclopedia, term definitions in GLOSSARY.md.*


---


## 11 · Useful commands — natural language that works

The pipeline is conversational: you talk to it in plain English and it figures out the right workflow step. A dedicated reference for natural-language triggers, combined requests, and the phrases that reliably produce each deliverable is in the **Quick Guide** (§ Useful commands). The single most useful phrase to know:

> **"Can you work from this to get me the full deliverables?"**

Upload your antiSMASH ZIP or Mamey package alongside that phrase and the chat runs the engine, presents all outputs, and offers the complete deliverable set — figures, triage board, Mode B cards, fermentation cards, and the compiled analysis report. It works for new analyses and for continuing prior sessions equally well. The chat reads the package context and picks up from where the last session ended.

For the full list of trigger phrases, combined-request patterns, and workflow control commands, see `docs/GUIDE/02_Quick_Guide.md` § *Useful commands*.

### 11.1 · The evidence-channel commands (v9.7.176–182)

These back the three-channel Mode B workflow (§4.2a). All are safe to run on their own:

- **`mamey kcb-frontpage <antismash_dir>`** — the named KCB leads per region, ranked, each with its
  corroboration tier (STRONG / COINCIDENTAL / LARGE_GENERIC). Run this first on any strain; it is
  the cheapest, highest-signal read and it catches named compounds a scanner would spend effort
  re-deriving.
- **`mamey blastp-online --package <gbk> --bgc <ID>`** — per-gene NCBI BLASTp for one BGC, with the
  CONFIRM/REFINE/OVERTURN reconciliation and the §9 cluster reads (coherence, function, novelty).
  Fail-closed; batches ≤10 proteins, giant proteins (>2500 aa) solo.
- **`mamey blastp-round --package <pkg> [--full-top 3] [--run]`** — the phased strain plan: full
  per-gene BLASTp for the top-N BGCs (so complete evidence is back before their cards are authored)
  plus one representative protein for every other BGC, saccharides included. Dry-run by default —
  it prints the plan and the submission-time estimate; add `--run` to submit.
- **`mamey hmm-adjudicate <region.gbk> [--locus <lt>]`** — the offline domain readout: ordered HMM
  hits per gene, module grammar, and the BLASTp-vs-antiSMASH tie-breaker.
- **`mamey figures {diagram|atlas|ani} …`** — the three publication figures (gene-arrow diagram,
  circular genome atlas, all-vs-all ANI heatmap). Needs the add-on figure wheels.

## Citation-Compact Provenance and Citation Status

Sapote-Mamey v9.7.140 uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another ChatGPT/web-literature session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope. The older reader-facing scope field should not appear in current citation-compact outputs.

### ChatGPT wrapper timeout after visible PASS

In capped ChatGPT/container sessions, the outer tool wrapper can time out after Mamey has already printed a terminal PASS and written manifest/checksum files. Treat this as an audit condition, not an automatic success. A run may be trusted only when the package validator passes, the package ZIP or run directory opens cleanly, required checksums verify, and `package_status.json` / `run_phase_receipts.jsonl` agree with the terminal status. If the wrapper times out during package sealing and validation cannot be completed, rerun validation or treat the package as incomplete.
