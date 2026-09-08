# Operating directives — intake/batch, small-N deliverables, ecology grounding
**Sapote–Mamey · authoritative; referenced from SESSION_START_MANIFEST §5**

Two failure modes seen in the field, plus the strict line between them:
- the **extraction layer** (ChatGPT/Mamey) grinding one strain for 17 minutes instead of doing an intake and batching;
- the **judgment layer** (Claude/Sapote) refusing legitimate per-strain deliverables on a small cohort, *and* the opposite risk of fabricating ungrounded ecology to avoid refusing.

The point of this doc is to force what is genuinely doable and forbid what isn't — both strictly.

---

## 1 · Intake-first + batch + stall guard (extraction layer)
1. **Intake first.** On any multi-file set, inventory **every** input ZIP → strain ID / taxonomy / source / release, and announce the batch plan (committed, deferred, sessions needed) BEFORE running a single strain.
2. **Drive the batch with the harness, not by hand.** `tools/intake_harness.py --inputs <dir> --outdir <out> --registry <reg.csv> --metrics <m.csv> --resume [--source "..."] [--release PUBLIC|PRIVATE]`. It runs the set through the engine + Diagnostic Rescue, records per-strain wall-time/RSS, and `--resume` skips finished strains so a timeout is safe to re-run.
3. **Stall guard (the 17-minute fix).** Mamey never re-runs antiSMASH — it consumes the cached parse. A single strain taking many minutes is an **input/parse** problem, not slow compute. Checkpoint, continue the batch, and diagnose the stalled strain via `prompts/RUN_DIAGNOSIS_PROMPT.md`. Never loop/retry one strain for minutes.

## 2 · Small-N is not a disqualifier (judgment layer)
The full per-strain suite is produced at **any N ≥ 1**. `tools/check_deliverable_suite.py` enforces the 13 §A items fail-closed against `FULL_RUN_PROFILE.md` (tiered Mode B: Full / candidate / abbreviated / one-line; hard batch rule >60 BGCs → groups of 15, announced, no silent omission). Never decline a per-strain deliverable for "too few strains" or "not qualified." In scope at N≥1: BGC-by-BGC Mode B · cassette registry + §34 hallucination-trap · separate AB/AF DAPR · RG-GMCI for every multi-contig genome (Mamey wrote the evidence; Sapote promotes it) · resistance/self-protection · missing-hallmark + negative-evidence · metabolomics/fermentation/induction/extraction/assay planning · Technical Report + Bench Guide + Layperson-Ranked Guide · per-strain workbook + dated ZIP.

## 3 · Ecology grounding — the strict line
**Interpretation is source-independent.** Sapote reads the GENOME / BGC evidence; the isolation source does not enter the biosynthetic-capacity call. So an unknown source **never blocks** the per-strain ecology read — and a known source is **never over-read** into a functional claim. The true ecological role of most environmental actinomycetes is genuinely unknown; isolation source is a weak, often-unreliable proxy (haphazard collection, inexperienced isolators).

| Item | Status at N≥1 | Rule |
|---|---|---|
| Per-strain ecological **interpretation** | **DO IT — never refuse, source or no source** | General, well-supported framing: actinomycetes broadly carry antimicrobial / defensive biosynthetic capacity. Claim-safe, capacity-level, tagged `assumed`. Same interpretation whether source is known, unknown, or unreliable. |
| **Isolation source** | **provenance only — never a functional claim** | Report a known source as caveated provenance; never escalate it into ecology ("bee-associated → co-evolved symbiont"). Unknown source is fine — it does not change the interpretation. |
| Habitat-keyed comparisons (CCSM) | **exploratory + caveated** | Pattern-finding over isolation categories, explicitly flagged isolation-source ≠ function; N-limited at small cohorts. Never a functional assertion, never a gate on the per-strain suite. |
| Deep literature reviews | **doable but paced** | Verified citations only (DOI/PMID/PMCID, real numbers from full text, claim-safe, copyright-limited). Time-boxed pass across top AB+AF leads — never an unverifiable citation. |
| Project-bundle **aggregates** (cross-strain rankings, RG-GMCI / cassette-family / hallucination stats, qualified-null/validation, completion audit + manifest + SHA-256) | **after per-strain** | Aggregate finished runs; correct sequencing, not foot-dragging — never a reason to defer the per-strain suite. |

## 4 · What "be strict" means here, in one line
Produce every per-strain deliverable (ecology interpretation included) at any N, grounded in the genome and independent of isolation source — **and** never over-interpret the source into a functional/ecological claim, never fabricate, never emit aggregates before the per-strain runs exist. Refusing on unknown source and over-reading a known source are *both* violations; the interpretation comes from the genome, not the collection label.
