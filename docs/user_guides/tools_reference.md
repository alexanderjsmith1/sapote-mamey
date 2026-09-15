# Sapote–Mamey Tools Directory Reference

**Bundle v9.7.430 · Engine 1.9.164** — re-grounded 2026-09-14 (Eggplant lane).

> **The per-script inventory that used to live here has been retired, not lost.**
> It is now generated, not hand-maintained:
>
> | What you want | Where it lives now | How it stays current |
> |---|---|---|
> | Every script in `tools/` + its docstring | [`docs/TOOLS_INVENTORY.generated.md`](../TOOLS_INVENTORY.generated.md) — **364 tools** | `tools/gen_tools_inventory.py`; `--check` verifies sync |
> | Every `mamey_run.py` subcommand | [`docs/COMMAND_CATALOG.generated.md`](../COMMAND_CATALOG.generated.md) — **113 canonical commands** (2 aliases folded in) | `tools/gen_command_catalog.py`; `--check` fails the build when stale |
> | External tools (antiSMASH, BiG-SCAPE, IQ-TREE, GToTree, BLAST+, SPAdes) | [`docs/EXTERNAL_TOOL_INVENTORY.md`](../EXTERNAL_TOOL_INVENTORY.md) | manual, versions + citations |
>
> **Why the change.** The inventory formerly in this file was compiled by hand on 2026-07-09 at
> bundle v9.7.241 and listed **107 scripts**. The generated inventory now lists **364**. A hand-maintained
> copy of a machine-derivable list drifts silently and was already covering under a third of the
> directory; the generated surfaces are gated by their own `--check` and cannot drift unnoticed.
> The counts above are copied from the generated files; run each generator's `--check` before citing them.
>
> **Do not re-add a manual script list here.** Check the generated inventory *before* writing a
> new tool, as its own header instructs.

## What remains in this file

Sections 14 onward: material a docstring generator cannot produce — real execution receipts,
gate semantics, the card readiness state machine, and the toolchain notes. These are human
observations about *behaviour*, not descriptions of *existence*.

---

## Section 14: Live Tools Verification — What Actually Runs

> **Currency note (added 2026-09-14):** the verification receipts in this section were recorded
> against **bundle v9.7.241 on 2026-07-09** and have **not** been re-executed since. They are
> retained as a historical receipt of what ran at that version, not as a claim about v9.7.430.
> Re-running this matrix is tracked as an open item; until then, treat the "Confirmed" column as
> "confirmed at v9.7.241".


*Commands verified to run successfully in bundle v9.7.241, 2026-07-09. All outputs are from real execution against the teicoplanin calibration package.*

### Verified command matrix

| Command | Input | Output | Confirmed |
|---|---|---|---|
| `mamey doctor` | (no input) | Dependency/permission pre-flight report | ✅ 18.8s total |
| `mamey inspect <zip>` | antiSMASH ZIP | Pre-run preview: region count, GBK contents | ✅ |
| `mamey run --mode gold` | antiSMASH ZIP | Sealed package, 26 figures, compiled report | ✅ 18.8s wall |
| `mamey validate <pkg>` | Sealed package | JSON gate report: file_presence, checksums, rggmci | ✅ MAMEY_COMPLETE |
| `mamey list-bgcs <pkg> --json` | Sealed package | JSON BGC inventory with all scores | ✅ |
| `mamey emit-modeb-template --bgc BGC001` | Sealed package + BGC ID | §1–§30 template with gene table pre-filled | ✅ 109 lines |
| `mamey render-all-figures <pkg>` | Sealed package | 5 figure modules, 26 figures total | ✅ |
| `mamey workflow <pkg> --json` | Sealed package | W0–W10 gate status with receipts | ✅ W0-W2 PASS |
| `tools/preflight_zip_hygiene.py <zip>` | antiSMASH ZIP | Clean/dirty assessment | ✅ OK |
| `tools/gen_marker_catalog.py --check` | (live patterns) | Drift check: 14 tables in sync | ✅ |
| `tools/sapote_workflow.py <pkg>` | Sealed package | W0–W10 ledger markdown | ✅ 3/11 PASS |
| `tools/claim_safety_linter.py <md>` | Markdown file | Finding list with line annotations | ✅ 2 findings |

### Tools that require additional arguments (not run but syntax verified)

**`tools/check_deliverable_suite.py`** — requires `--manifest MANIFEST` (a filled `DELIVERABLE_MANIFEST_*.md`). Not runnable until the deliverable manifest has been generated and filled.

**`tools/assembly_qc_check.py`** — takes `--snapshot` or `--banked-dir`, not `--package`. Call with a cohort bank directory, not directly with a package.

**`tools/sapote_md_preflight.py`** — requires both `input_md` and `output_md` positional arguments (writes a preflight-processed copy to output).

**`tools/build_workbook.py --full`** — requires `--banked-dir` (a cohort bank populated by `ingest_package.py`). Cannot run on a single package directly.

### Tools output format notes

**`mamey workflow --json`** — produces the same content as the markdown output but machine-readable. The status values are: `PASS`, `PENDING`, `BLOCKED`, `N_A`. The `receipt` field contains the specific artifact reference (file name + size + content summary) that confirmed the PASS, or the blocking reason.

**`mamey list-bgcs --json`** — produces a JSON array, one object per BGC. The array is directly usable by downstream tools. The `--axis` flag selects sort order (`rank`, `ab`, `af`, `novelty`); `--top N` limits output count.

**`mamey emit-modeb-template`** — the output goes to stdout by default; redirect to a file for authoring. The template includes a pre-filled gene table from `gene_context.jsonl`, the BGC's scores from the triage board, and the over-merge warning when applicable.

**`mamey render-all-figures`** — non-blocking per module. If one module fails (e.g. domain-level fails because deep_data.json is empty), the others continue. The summary at the end reports per-module results.

**`tools/gen_tools_inventory.py`** — writes the full tools inventory to `docs/TOOLS_INVENTORY.generated.md`, injects a compact `name — summary` list into the generated block of `docs/BUNDLE_CAPABILITIES.md`, and also outputs "wrote inventory: N tools" to stdout. The inventory is a structured markdown table of all tools/scripts with docstrings extracted. For a connection-aware review, run `python tools/gen_tools_inventory.py --connections --format tsv --output tool_connections.tsv`. That audit reports exact source hashes, executable interface, source/CLI consumers, tests, path-filtered non-historical documentation references, manifest membership, declared lifecycle, personal-path literals, external-contact markers, and two transparent evidence scores. The scores measure wiring and operational support only; they do not measure scientific value, correctness, acceptance, or release readiness. The marker columns are review cues, not proof that a default is unsafe or that external contact occurs.

---

## Section 15: Tools Quick Reference Card

For field use — the most common tools and their essential flags.

```bash
# --- BEFORE A RUN ---
mamey doctor                               # pre-flight: Python, deps, permissions
preflight_zip_hygiene.py <zip>             # check for macOS artifacts, oversized files
mamey inspect <zip>                        # preview: region count, organism, GBK structure

# --- RUN ---
python -m mamey run \
  --input-zip <zip> --strain <ID> \
  --taxonomy "Genus sp." --source "host, location" \
  --release PUBLIC|PRIVATE \
  --mode gold --json-evidence bounded \
  --outdir runs/

# --- VALIDATE ---
mamey validate runs/<ID>/package           # → MAMEY_COMPLETE or MAMEY_COMPLETE_WITH_ISSUES

# --- FIGURES ---
mamey render-all-figures --package <pkg>   # run if --capped-session suppressed figures

# --- EXPLORE OUTPUTS ---
mamey list-bgcs <pkg> --json              # BGC inventory with all scores
mamey list-bgcs <pkg> --axis af --top 5  # top 5 by antifungal score
mamey explain <pkg>                        # narrative walkthrough

# --- MODE B ---
mamey emit-modeb-template \
  --package <pkg> --bgc BGC001 > BGC001_card.md    # emit §1–§30 skeleton
mamey verify-modeb --package <pkg> --bgc BGC001    # validate authored card

# --- WORKFLOW GATE ---
mamey workflow --package <pkg>             # W0–W10 markdown ledger
mamey workflow --package <pkg> --json     # W0–W10 machine-readable
mamey workflow --package <pkg> --strict   # exit non-zero if any mandatory step incomplete

# --- COMPILE ---
mamey compile-report --package <pkg>       # auto-compile report
mamey compile-report --package <pkg> --strict  # exit non-zero if SAPOTE slots open
mamey compile-report --package <pkg> --pdf  # also render Boss-Ready PDF via tools/md_to_pdf.sh (refuses on unfilled slots)
mamey compile-report --package <pkg> --pdf --allow-unfilled-pdf  # render the PDF even with unfilled slots (skeleton)

# --- BANK AND BUILD ---
tools/ingest_package.py \
  --package <pkg> --ww WWGP0000000 \
  --merge --banked-dir cohort/

tools/build_workbook.py \
  --workbook project_master.xlsx \
  --banked-dir cohort/ --full

# --- RELEASE ---
tools/gen_marker_catalog.py --check       # verify catalog matches source
tools/sync_version.py --check             # verify version strings consistent
tools/preflight_zip_hygiene.py <zip>      # clean release check
tools/check_tier_parity.py --tiers-dir . # all-tier parity gate
tools/claim_safety_linter.py <md>        # check claim safety in narrative text
```

**compile-report `--pdf` publication artwork.** The PDF path validates every figure at the declared
7.2-inch double-column width before writing render Markdown. Live-text SVG is preserved through vector
PDF conversion when `cairosvg`, `rsvg-convert`, or `inkscape` is available. Only if vector conversion is
unavailable may the compiler make a native-width raster fallback, which must still provide at least 300
effective DPI. Existing PNG thumbnails that would be enlarged are refused with
`FIGURE_EFFECTIVE_DPI_INSUFFICIENT`; metadata DPI and PDF-derived screenshots do not satisfy the gate.
This fail-closed check prevents a standalone screen PNG from becoming blurred publication artwork.
Install `cairosvg` via the render extra so the vector-preserving path is available wherever the compiled
PDF is built:

```bash
pip install '.[render]'   # cairosvg — also folded into '.[all]'
```

---

*v2 additions: Sections 14–15 (live verification, quick reference card) · Bundle v9.7.241 · 2026-07-09*

---

## Section 16: New Tools (v9.7.243–246)

### `tools/file_atlas.py` — describe every Python file from the source

**Added:** v9.7.243. Built for the Bunny Hop Audit Game (`debugging_modules/BUNNY_HOP_AUDIT_GAME.md`): "you cannot audit what you cannot see."

Walks `mamey/` and `tools/` with `ast` and emits one row per file. Nothing is inferred and no list is hardcoded — every column is read from the real tree.

**Columns:** `path`, `loc`, `summary` (first docstring line), `n_defs`, `n_classes`, `imports_internal` (fan-out), `imported_by` (fan-in), `cli_verbs` (subcommands registered in this file), `test_refs` (test files naming this module), `orphan`.

**The `orphan` column is the interesting one.** A module that nothing imports, that no CLI verb reaches, and that no test names, is a candidate for the audit's REDUNDANCY inspector — or for the defect class this project keeps hitting, where **a capability exists and nothing invokes it** (see Development Issues Compendium, Group 14).

```bash
python3 tools/file_atlas.py --out docs/FILE_ATLAS.csv --md docs/FILE_ATLAS.md
python3 tools/file_atlas.py --orphans     # just the orphan list, for the bunny-hop roll
```

| Flag | Effect |
|---|---|
| `--out PATH` | CSV output path |
| `--md PATH` | Markdown summary path |
| `--orphans` | Print orphan candidates only; no files written |

**Live receipt on bundle v9.7.246:**

```
280 files under mamey/ and tools/
74,981 total lines
35 orphan candidates (no importer, no CLI verb, no test)
57 files no test names at all
```

**Highest fan-in (from `docs/FILE_ATLAS.md`) — change these carefully:**

| File | Imported by | LOC |
|---|---:|---:|
| `tools/_wbio.py` | 38 | 125 |
| `mamey/models.py` | 13 | 397 |
| `mamey/crosswalk.py` | 11 | 238 |
| `mamey/antismash_evidence.py` | 9 | 1,233 |
| `mamey/figure_policy.py` | 8 | 56 |
| `mamey/source_scans.py` | 8 | 1,733 |
| `mamey/_gbk_shim.py` | 7 | 139 |
| `mamey/modeb_structure_gate.py` | 7 | 1,036 |

Both `_wbio.py` (38 importers, 1 test before v9.7.243) and `crosswalk.py` (fan-in 11) were subsequently hardened — the atlas identified them as the highest-risk files, and the audit went there next. This is the tool doing its job.

**Known limitation, found and fixed before shipping:** the first pass called `verify_release_identity.py` an orphan. It is invoked by `tools/release.sh`, which the AST scanner did not read. Shell and gate-registry invocations now count. Orphan count dropped 42 → 35. The lesson generalises: an AST scan sees Python imports, not shell invocations, not YAML, not a `gate_registry.tsv` row.

**Output artifacts:** `docs/FILE_ATLAS.csv` (machine-readable, one row per file) and `docs/FILE_ATLAS.md` (four sections: Highest fan-in · Largest files · Orphan candidates · Every file).

---

### `tools/check_monolith_freshness.py` — keep the parent design doc's anchor honest

**Added:** v9.7.243, WIRED (registered in `tools/gate_registry.tsv`).

`docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` is the parent design controller, referenced by 20 files including `prompts/CLAUDE_SYSTEM_PROMPT.md`. It is deliberately **not** bumped every patch — its content is reviewed at checkpoints. That convention is sound. What is not sound is the anchor line drifting silently: at v9.7.242 the monolith still claimed to be vetted against v9.7.6 and stated `current bundle 9.7.57 / engine 1.9.64` — **185 cuts of drift, with no signal.**

**The gate does not demand a re-read. It demands that the monolith state, truthfully, how far behind it is.**

**Four checks:**
1. The monolith exists and names a `vetted against` bundle version.
2. The `current bundle X / engine Y` parenthetical, if present, matches the live `pyproject.toml` / `BUILD_STAMP`.
3. The drift (live bundle patch − vetted patch) is reported, and fails above `--max-drift`.
4. **No retired doctrine is present** — assembly tiers 66/50/33, per-BGC BSL-2 flagging, AS_SCRUB, the PUBLIC/PRIVATE figure divider. These are decisions the project has explicitly reversed, and a fresh chat reads the monolith first.

```bash
python3 tools/check_monolith_freshness.py                # default max-drift
python3 tools/check_monolith_freshness.py --max-drift 10
python3 tools/check_monolith_freshness.py --quiet
```

| Exit | Meaning |
|---|---|
| 0 | Fresh enough and doctrinally current |
| 1 | Stale anchor or retired doctrine present |
| 2 | Monolith missing |

**Live receipt on bundle v9.7.246:**

```
monolith: vetted v9.7.242 | live v9.7.246 | drift 4 patches | 450,214 chars
check_monolith_freshness: PASS (anchor honest, no retired doctrine)
```

**Negation awareness.** The gate false-positived on its own first run, flagging a freshly written "no per-BGC BSL-2 flagging" as an assertion of the doctrine it denies. A negation-aware window was added — the same lesson the v9.7.233 novelty lint learned. It still fails on a genuine assertion (`GOOD >= 66%`).

---

## Section 17: Gate Additions (v9.7.246–.256)

### `PHANTOM_LOCUS` — release-blocking referent validation

Not a standalone tool: a lint inside `mamey/modeb_structure_gate.py`, reachable through `mamey verify-modeb` and `authored_verify`.

**What it asks:** does every `ctgN_M` locus tag cited in this Mode B card exist in **this strain's own CDS table**?

**Why it exists:** the §4 authoring template hardcoded a real per-gene BLASTp result from *Amycolatopsis* sp. NPDC004378, which was templated verbatim into 74 cards across two strains — asserting a specific BLASTp outcome for strains on which no BLASTp had been run. Every existing guard passed those cards. None of them asked whether the cited gene existed. (Full account: Development Issues Compendium, Group 13.)

**How to invoke:**

```bash
mamey verify-modeb --package <sealed_pkg> --bgc BGC001    # loads known_loci automatically
```

`authored_verify` globs `<pkg>/*_cds_table.csv` and `<pkg>/cds_table.csv` to build `bgc_context["known_loci"]`. Without a sealed package there is no CDS table, and **the lint is silent** — it cannot judge what it cannot see, and a false accusation of fabrication is worse than none.

**Severity:** ERROR. Added to `_READINESS_BLOCKING` alongside `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`, and `FACT_MISMATCH`. A card citing a foreign locus cannot reach `EVIDENCE_MATRIX_VALIDATED` and therefore cannot be presented.

**Verified against the real AS-XXX package:** 758 loci loaded; `ctg12_71` not among them; the leaked sentence raises ERROR and drops `readiness_state` to `DRAFT`. A card citing that strain's real loci passes clean.

**Operational consequence:** the 74 already-authored cards are not repaired by the fix. Re-run `verify-modeb` against them with a sealed package and every one will flag. **Every §4 and §16 paragraph containing `ctg12_71` should be deleted, not reworded** — there is no BLASTp result to reword.

### `LOCUS_BGC_MISMATCH` — real locus cited under the wrong BGC (v9.7.256)

Sibling of `PHANTOM_LOCUS` in `mamey/modeb_structure_gate.py`, reached through `verify-modeb` / `authored_verify`. Where `PHANTOM_LOCUS` asks *does this gene exist in this strain at all*, `LOCUS_BGC_MISMATCH` asks *does this gene, which does exist, belong to the BGC it is cited under*.

**What it asks:** for a `ctgN_M` that is a real member of this strain's CDS table, is it cited under its home BGC, or co-cited under a different BGC it does not belong to?

**Why it exists:** the AS-XXX BGC006/BGC010 leak class — templated boilerplate carried from one BGC's session into another's card attributes a real gene to the wrong cluster. The gene is real (so `PHANTOM_LOCUS` stays silent), but the attribution is fabricated. `authored_verify` builds per-BGC membership so the lint can tell a real gene cited under the wrong BGC from a correctly-placed one.

**Severity:** ERROR → the card drops to `DRAFT` (Section 18) and cannot be presented. It is **not** a member of the four-code `_READINESS_BLOCKING` set; it blocks via the any-ERROR path.

### `PANEL_ABSENT_CLAIM` — per-gene BLASTp result asserted for a BGC with no panel (v9.7.256)

Sibling lint (same file / entry points). Guards the independent-homology channel against fabricated results.

**What it asks:** does the card state a per-gene BLASTp outcome for a BGC that has **no BLASTp panel** in this package?

**Why it exists:** a BLASTp result for a BGC whose panel was never built is a fabricated observation (the same AS-XXX BGC006 class). `authored_verify` records which BGCs actually have a panel so the lint can flag a per-gene claim on a BGC with none.

**Keys on panel *selection*, not returned alignments (residual gap, stated):** a standard run builds a selection FASTA for *every* BGC, so this lint does **not** catch a fabricated per-gene result on a BGC that has a panel selection but was never actually run (reproduced on `S_erythraea` BGC017). The residual gap is "asserted result vs actual returned alignments"; a future gate closing it should extend `PANEL_ABSENT_CLAIM` to require a results artifact, not add a new gate.

**Severity:** ERROR → `DRAFT`; blocks via the any-ERROR path, not a `_READINESS_BLOCKING` member.

---

## Section 18: Card Readiness State Machine

Documented here because `verify-modeb` reports it and no other section covers it. Source: `mamey/modeb_structure_gate.py:readiness_state`.

```python
_READINESS_BLOCKING = {"NOVELTY_CONTRADICTION", "INTERNAL_CONTRADICTION", "FACT_MISMATCH",
                       "PHANTOM_LOCUS"}


def readiness_state(findings, quality_tier: Optional[str] = None) -> str:
    """Return a mechanical validation state, never an owner/release state.

    Character/depth diagnostics and deterministic lints cannot confer scientific
    acceptance, integration, rendering approval, release approval, or publication approval.
    """
    findings = list(findings or [])
    if any(f.get("severity") == "ERROR" for f in findings):
        return "DRAFT"
    if quality_tier in (None, "STUB", "UNKNOWN"):
        return "DRAFT"
    if {f.get("code") for f in findings} & _READINESS_BLOCKING:
        return "STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS"
    return "EVIDENCE_MATRIX_VALIDATED"
```

| State | Meaning | May be presented? |
|---|---|---|
| `DRAFT` | Any ERROR finding, **or** the card is a STUB / depth-unverified | No |
| `STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS` | Depth is adequate, but a correctness check fails (one of the four blocking codes) | No |
| `EVIDENCE_MATRIX_VALIDATED` | Depth adequate **and** no correctness block | Mechanically clear; presentation still needs owner judgment |

**Only `EVIDENCE_MATRIX_VALIDATED` should flow into user-facing documents.** This is the mechanical presentation gate, not a release or scientific-acceptance state (the function's own docstring says so). A card that is structurally complete, adequately deep, and claim-safe can still be `STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS` rather than `EVIDENCE_MATRIX_VALIDATED` — because a fact in it contradicts the package, or a locus in it belongs to another organism.

Note the asymmetry: an ERROR-severity finding drops a card all the way to `DRAFT`; a blocking *code* at WARN severity holds it at `STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS`. `PHANTOM_LOCUS` is emitted at ERROR severity, so a phantom locus produces `DRAFT`.

---

## Section 19: BLASTp toolchain + release-qa (v9.7.247–.260, CLI synced v9.7.260)

The independent per-gene homology channel and its ingest/iterate commands, plus the release gate. These are `mamey` subcommands (not `tools/` scripts); descriptions are from the registered CLI (`mamey <cmd> --help`), verified against the tree at v9.7.260.

**§4 authoring — offline path preferred (v9.7.260).** A Mode B lead card's §4 is authored *after* the BLASTp panel exists, but there are two ways to produce the same `<BGC>_online_blastp.csv` panel and the offline one avoids live polling:

- **token-friendly / offline (preferred when results are in hand):** if NCBI BLAST has already been run, ingest the hit-table with zero network via `mamey ingest-blastp` — no RID poll, no ~1–2 min/query wait.
- **live:** `mamey blastp-online` submits to NCBI and polls; use only when no pre-run results exist.

With no results at all, the honest read is "antiSMASH Pfam, unverified" — never fabricate (see `PANEL_ABSENT_CLAIM` / `PHANTOM_LOCUS`, Section 17).

**`mamey bgc-blastp-panel`** — Export up to two representative translated proteins per BGC as chunked FASTA files for manual BLASTP. The panel *selection* is what downstream gates read to decide a BGC "has a panel" (`PANEL_ABSENT_CLAIM`).

**`mamey blastp-online`** — Per-gene NCBI web BLASTp for a BGC (independent homology channel; fail-closed if biopython/network absent — actionable message, not a traceback). Its banner now points at the offline `ingest-blastp` route to skip live polling.

**`mamey blastp-ebi`** — EBI fallback BLASTp transport (no nr; DB-tagged provenance; coverage-preserving XML path).

**`mamey blastp-round`** — Plan/run a phased strain BLASTp round (full top-N + 1 per remaining BGC).

**`mamey blastp-followup`** — Parse NCBI BLASTP Hit Table / XML2 results and make the next iterative, residue-safe BLASTP queue files.

**`mamey ingest-blastp`** — Ingest an NCBI BLASTp HitTable CSV (+ optional Alignment XML) into a master workbook's `B5_BLASTp_Hits` sheet; with `--package`, mirrors the panel to `<package>/blastp_online/<BGC>_online_blastp.csv`. This is the offline, zero-network path.

**`mamey modeb-blastp`** — Emit per-BGC BLASTP FASTA batches from the panel manifest (Mode B §16 automation).

**`mamey hmm-adjudicate`** — Ordered HMM domain readout for a BGC (intrinsic structure; offline tie-breaker that complements BLASTp when it disagrees with the antiSMASH call).

**`mamey release-qa`** — Run release QA gates: Legacy Feature Matrix + Dual-LLM Handoff Receipt.

*Batch rule (v9.7.252): a submission closes on protein count OR a 30,000-aa `RESIDUE_BUDGET`, whichever hits first; `MAX_BATCH` stays 30 and `DEFAULT_BATCH` is 10 (the courteous default used when the caller omits `batch_size`); giants (>2,500 aa) run solo; `SUBMIT_GAP_S` spaces submissions.*

*Mode B referent lints (v9.7.246/.256): `PHANTOM_LOCUS` (locus not in this strain's CDS table), `LOCUS_BGC_MISMATCH` (real locus cited under the wrong BGC), `PANEL_ABSENT_CLAIM` (per-gene BLASTp result asserted for a BGC with no panel). All ERROR-severity → `DRAFT`. Full detail in Section 17.*

*Section 19 added v9.7.260; command descriptions from the registered `mamey <cmd> --help`.*

---

## Section 20: New post-seal subcommands & deliverables (v9.7.338)

Twelve sign-off-gated capabilities that consume an **already-sealed package** (or a directory of
them) and emit an extra deliverable. Like `render-figures` / `cohort-figures` / `ingest-receipts`,
every one is post-seal and non-blocking: it reads facts the engine already computed and **never
re-runs the engine, moves a score, or touches a published tier**. Non-scoring unless noted;
capacity-level, judgment deferred.

```bash
# --- CROSS-STRAIN LEDGERS ---
mamey cohort-leads    --runs-dir <runs_dir> [--out COHORT_PRIORITY_LEADS.csv]   # union Exceptional+High leads → one ranked CSV
mamey cohort-assemble --runs-dir <runs_dir> [--out COHORT_MASTER.csv] [--xlsx]  # many sealed packages → one master table (+ siblings)

# --- EVIDENCE / FALSE-POSITIVE LAYER ---
mamey comparator-coverage <package> [--cohort-runs-dir <runs_dir>]  # two-denominator MIBiG comparator coverage (report-only)
                                                                     # standalone: python -m mamey.mibig_comparator_coverage <package_dir> [--cohort-runs-dir <dir>]

# --- ANTIFUNGAL + INTERPRETIVE DELIVERABLES ---
mamey af-dossier   <root> [--out DIR] [--activity-table CSV] [--depth N]  # AF leads x optional measured Candida activity (report-only)
mamey good-guesses <root> [--out DIR] [--pdf] [--docx] [--depth N]       # claim-safe interpretive priors (solid/rare/remarkable/notable/interesting)
                                                                          # standalone: python -m mamey.good_guesses <ROOT|package_dir> --out <DIR> --pdf --docx

# --- DOCUMENT + FIGURE EXPORT ---
mamey modeb-export <card.md|mode_b/> [--outdir DIR] [--format docx|pdf|both]  # authored Mode B card → .docx + .pdf (reportlab)
python -m mamey.kcb_locusmap --zip <zip> --contig <NODE> --out-dir <dir> \
    --strain-id <ID> --bgc-id BGC### [--products "..."] [--top-n 6]           # offline KCB comparative locus map (PNG/SVG + data.csv)
                                                                              # or: --kcb-txt <knownclusterblast.txt> --out-dir <dir> --stem BGC###

# --- COUNT / NOVELTY / REFERENCE (advisory) ---
mamey domain-reference  --package <pkg> [--out FILE]            # bundled Mode-B domain-reference dictionary
mamey realistic-count   --package <pkg> [--out FILE]            # honest corrected BGC-count denominator
mamey novelty-shortlist --package <pkg> [--top 30] [--out FILE]  # composite multi-signal novelty shortlist

# --- ANALYSIS QC + MODE-B INTERPRETATION GATES ---
mamey signoff [tree.treefile ...] [--minutes N]                          # "would a master's student sign off?" tree QC (advisory, exit 0)
mamey verify-modeb --package <pkg> --bgc BGC### --interp [--interp-strict]  # add WARN-only INTERP_* judgment checks to verify-modeb
                                                                           # strict authoring gate: python -m mamey.modeb_interp_gate <card.md> [--strict]
```

**Notes.**
- **`comparator-coverage`** emits `<STRAIN>_3b_comparator_coverage.csv` + `_summary.json`. It is the
  false-positive killer: a named-MIBiG-family "lead" that survives only one of the two coverage
  denominators is exposed as low-specificity rather than surfaced. Report-only in .338 — its scoring
  wire (suppression-only, guard-gated) is a future sign-off-gated change and is NOT active.
- **`good-guesses`** writes `GOOD_GUESSES.{md,csv}` (+ `.docx` / `.pdf` on request). Each notable BGC
  gets ONE best claim-safe read, a tag (solid / rare / remarkable / notable / interesting), a
  confidence, and the resolving experiment; a per-page claim-safety footer is included.
- **`modeb-export`** — `reportlab` (PDF) is a core dependency in `pyproject.toml`, installed by `pip install -e .`;
  `python-docx` is only in the `documents` / `all` extras, so the DOCX path degrades gracefully
  (`SKIPPED_NO_DOCX`) rather than failing when it is unavailable.
- **`figures kcb-locusmap`** degrades to a clear message + non-zero exit (never a traceback) when
  matplotlib is absent; it reads only a sealed input ZIP (or an extracted txt) and cannot fail a run.
- **`verify-modeb --interp`** only *adds* WARN-severity `INTERP_*` findings — the structure gate's
  PASS/FAIL and exit code are unchanged (a card can be green and still show interp warnings).

**Non-feature .338 changes reflected here:** the **§4 Mode-B evidence gate now bites (MB-01)** (the
evidence-grid check is enforcing, not advisory), the **NAPAA standing rule now follows the registry
(RG-01)** (driven by `rules_registry.json`, not a hardcoded pattern — same behaviour, single source),
and the redaction wording is corrected (E2E-03): AS-series strains are PUBLIC by default (PI decision
2026-07-06), fail-safe PRIVATE only for AJS- / PENDING- / unrecognized shapes.

---

*v3 additions: Sections 16–18 (file_atlas, check_monolith_freshness, PHANTOM_LOCUS gate, readiness state machine) · Bundle v9.7.246 · 2026-07-09*
*v4 additions: Section 17 extended with `LOCUS_BGC_MISMATCH` + `PANEL_ABSENT_CLAIM` (v9.7.256); Section 19 (BLASTp toolchain + release-qa, offline-preferred §4); header CLI-synced · Bundle v9.7.260 · 2026-07-11*
*v5 additions: Section 20 (twelve new post-seal subcommands & deliverables) · v9.7.338*
