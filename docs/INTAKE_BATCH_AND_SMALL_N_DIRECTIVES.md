# Operating directives — intake/batch, small-N deliverables, ecology grounding
**Sapote–Mamey project workflow policy; execution remains scoped by the current user task.**

Two failure modes seen in the field, plus the strict line between them:
- the **extraction layer** (ChatGPT/Mamey) grinding one strain for 17 minutes instead of doing an intake and batching;
- the **judgment layer** (Claude/Sapote) refusing legitimate per-strain deliverables on a small cohort, *and* the opposite risk of fabricating ungrounded ecology to avoid refusing.

The point of this doc is to force what is genuinely doable and forbid what isn't — both strictly.

---

## 1 · Intake-first + batch + stall guard (extraction layer)
1. **Intake first.** On any multi-file set, inventory **every** input ZIP → strain ID / taxonomy / source / release, and announce the batch plan (committed, deferred, sessions needed) BEFORE running a single strain.
2. **Drive the batch with the harness, not by hand.** `tools/intake_harness.py --inputs <dir> --outdir <out> --registry <reg.csv> --metrics <m.csv> --resume [--source "..."] [--release PUBLIC|PRIVATE]`. It runs the set through the engine + Diagnostic Rescue, records per-strain wall-time/RSS, and `--resume` skips only completion receipts matching the input bytes, bundle engine/resources, options and output package. Legacy or changed success records hold before package replacement; use a fresh reviewed output directory and registry. NEEDS_ANTISMASH remains retryable. An archive with region files in multiple parent directories is refused rather than selecting one assembly silently. Failed attempts without a remaining package may retry; an existing unbound package requires review and a fresh output directory.
3. **Stall guard (the 17-minute fix).** Mamey never re-runs antiSMASH — it consumes the cached parse. A slow strain requires phase-specific diagnosis; elapsed time alone does not establish an input/parse defect. Optional reference completion, scans, finalization or rendering can also take time. Preserve the current package/logs, confirm process ownership and cleanup, then continue only when resources permit; diagnose the stalled strain via `prompts/RUN_DIAGNOSIS_PROMPT.md`. Never loop/retry one strain for minutes.

## 2 · Small-N is not a disqualifier (judgment layer)
The full per-strain suite is produced at **any N ≥ 1**. `tools/check_deliverable_suite.py` checks the reported 13-row manifest text; it does not establish artifact or scientific completeness against `FULL_RUN_PROFILE.md` (tiered Mode B: Full / candidate / abbreviated / one-line; hard batch rule >60 BGCs → groups of 15, announced, no silent omission). Never decline a per-strain deliverable for "too few strains" or "not qualified." In scope at N≥1: BGC-by-BGC Mode B · cassette registry + §34 hallucination-trap · separate AB/AF DAPR · RG-GMCI for every multi-contig genome (Mamey wrote the evidence; Sapote promotes it) · resistance/self-protection · missing-hallmark + negative-evidence · metabolomics/fermentation/induction/extraction/assay planning · Technical Report + Bench Guide + Layperson-Ranked Guide · per-strain workbook + dated ZIP.

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

## Harness recovery and checker limits (.447 source)

The harness's CLI does not expose a per-input timeout or stall timer. `run_monitored` has an optional timeout parameter, but the normal engine call does not pass one (`tools/intake_harness.py:142–208,576–582`). Capped mode is a settings profile, not a guaranteed wall-clock bound; optional reference completion can still run (`mamey/cli.py:6150–6167`). Do not assume a timeout kills descendants or saves a persistent per-input log: the monitor owns the immediate child, captures output in a temporary file and attaches diagnostics to an exception. Save available diagnostics through the authorized task's checkpoint policy.

Harness exit 0 means no attempted row was `RUN_FAILED`; it can include `NEEDS_ANTISMASH`, while verified resume skips are not counted as attempted rows (`tools/intake_harness.py:665–686`). Inspect registry, metrics, completion receipts and the exact package before reporting whole-set completion. A registry row alone is not a resume receipt; retain existing unbound packages and use a fresh reviewed output root/registry after a binding hold.

The deliverable checker requires reported statuses/reasons and certain gold text/count fields (`tools/check_deliverable_suite.py:25–79`), but does not open artifact paths, compare checksums, bind counts to the package, require unique rows or enforce the batch-size policy above. Its default mode is `standard`; pass `--mode gold` explicitly for the gold text checks (`:83–105`). It rejects JUDGMENT_PENDING but does not independently validate every other reported gold state. A missing standing-constraint line is not itself rejected. Preserve those gaps as independent checks; a zero exit cannot certify the suite's content, profile compliance or scientific validity. See [deliverable contract](DELIVERABLE_CONTRACT.md) and [the manifest template](DELIVERABLE_MANIFEST_TEMPLATE.md).

Small sample size alone does not justify discarding an authorized per-strain deliverable. Runtime, available evidence and user scope still determine what can actually be completed. State unresolved evidence and output holds honestly; no policy here grants new experimental, online, publication or release authority.
