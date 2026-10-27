# Operating directives — intake/batch, small-N deliverables, ecology grounding
**Sapote–Mamey project workflow policy; execution remains scoped by the current user task.**

Two failure modes seen in the field, plus the strict line between them:
- the **extraction layer** (Mamey) running one strain for many minutes instead of taking an intake and batching;
- the **judgment layer** (Sapote) refusing legitimate per-strain deliverables on a small cohort, *and* the opposite risk of fabricating ungrounded ecology to avoid refusing.

The point of this doc is to force what is genuinely doable and forbid what isn't — both strictly.

---

## 1 · Intake-first + batch + stall guard (extraction layer)
1. **Intake first.** On any multi-file set, inventory **every** input ZIP → strain ID / taxonomy / source / release, and announce the batch plan (committed, deferred, sessions needed) BEFORE running a single strain.
2. **Drive the batch with the harness.**
   `python tools/intake_harness.py --inputs <dir> --outdir <out> --registry <reg.csv> --metrics <m.csv> --resume [--source "..."] [--release PUBLIC|PRIVATE]`
   - New batches default to PRIVATE and source "not verified". Reviewed public inputs need `--release PUBLIC --source "<verified source>"`. PRIVATE is not redaction or permission to export.
   - `--inputs` takes ZIP files, folders or both. A folder is read one level deep: only the `*.zip` files directly inside it.
   - The harness names each strain from its ZIP filename, with assembly boilerplate removed. Inputs whose cleaned names collide get an assembly tag or a number. Check the names in the registry before you rely on them.
   - The harness runs each input through the engine and Diagnostic Rescue and records wall time and memory per strain. Each package lands in `<out>/<name>/package/`, with its completion receipt in `<out>/<name>/intake_completion_receipt.json`.
   - `--resume` skips an input only when its completion receipt matches the input bytes, engine, options and output package. A changed release, source, mode, taxonomy map, per-input timeout, engine or harness code, or Python interpreter puts the input on hold; use a fresh output folder and registry.
   - Without `--resume`, a rerun with the same output folder or registry holds every input that already has a package, a completion receipt or a success row.
   - `NEEDS_ANTISMASH` can be retried. An archive with region files in several parent folders is refused rather than picking one assembly. A failed attempt with no package left can be retried; an existing unbound package needs review and a fresh output folder.
3. **Stall guard.** Mamey never re-runs antiSMASH — it consumes the cached parse. A slow strain requires phase-specific diagnosis; elapsed time alone does not establish an input/parse defect. Optional reference completion, scans, finalization or rendering can also take time. Preserve the current package/logs, confirm process ownership and cleanup, then continue only when resources permit; diagnose the stalled strain via `prompts/RUN_DIAGNOSIS_PROMPT.md`. Never loop/retry one strain for minutes.

## 2 · Small-N is not a disqualifier (judgment layer)
The full per-strain suite is produced at **any N ≥ 1**. `tools/check_deliverable_suite.py` checks the reported 13-row manifest text; it does not establish artifact or scientific completeness against [`prompts/FULL_RUN_PROFILE.md`](../prompts/FULL_RUN_PROFILE.md) (tiered Mode B: Full / candidate / abbreviated / one-line; hard batch rule >60 BGCs → groups of 15, announced, no silent omission). Never decline a per-strain deliverable for "too few strains" or "not qualified." In scope at N≥1: BGC-by-BGC Mode B · cassette registry + §34 hallucination-trap · separate AB/AF DAPR · RG-GMCI for every multi-contig genome (Mamey wrote the evidence; Sapote promotes it) · resistance/self-protection · missing-hallmark + negative-evidence · metabolomics/fermentation/induction/extraction/assay planning · Technical Report + Bench Guide + Layperson-Ranked Guide · per-strain workbook + dated ZIP.

## 3 · Ecology grounding — the strict line
**Interpretation is source-independent.** Sapote reads the GENOME / BGC evidence; the isolation source does not enter the biosynthetic-capacity call. So an unknown source **never blocks** the per-strain ecology read — and a known source is **never over-read** into a functional claim. The true ecological role of most environmental actinomycetes is genuinely unknown; isolation source is a weak, often-unreliable proxy.

| Item | Status at N≥1 | Rule |
|---|---|---|
| Per-strain ecological **interpretation** | **DO IT — never refuse, source or no source** | General, well-supported framing: actinomycetes broadly carry antimicrobial / defensive biosynthetic capacity. Claim-safe, capacity-level, tagged `assumed`. Same interpretation whether source is known, unknown, or unreliable. |
| **Isolation source** | **provenance only — never a functional claim** | Report a known source as caveated provenance; never escalate it into ecology ("bee-associated → co-evolved symbiont"). Unknown source is fine — it does not change the interpretation. |
| Habitat-keyed comparisons (CCSM) | **exploratory + caveated** | Pattern-finding over isolation categories, explicitly flagged isolation-source ≠ function; N-limited at small cohorts. Never a functional assertion, never a gate on the per-strain suite. |
| Deep literature reviews | **doable but paced** | Verified citations only (DOI/PMID/PMCID, real numbers from full text, claim-safe, copyright-limited). Time-boxed pass across top AB+AF leads — never an unverifiable citation. |
| Project-bundle **aggregates** (cross-strain rankings, RG-GMCI / cassette-family / hallucination stats, qualified-null/validation, completion audit + manifest + SHA-256) | **after per-strain** | Aggregate finished runs; correct sequencing, not foot-dragging — never a reason to defer the per-strain suite. |

## 4 · What "be strict" means here, in one line
Produce every per-strain deliverable (ecology interpretation included) at any N, grounded in the genome and independent of isolation source — **and** never over-interpret the source into a functional/ecological claim, never fabricate, never emit aggregates before the per-strain runs exist. Refusing on unknown source and over-reading a known source are *both* violations; the interpretation comes from the genome, not the collection label.

## Harness recovery and checker limits

The harness has an optional `--per-input-timeout SECONDS`. By default there is no limit. An input that runs past the limit is recorded as `RUN_FAILED` with an `INPUT_TIMEOUT` message, and the harness moves on to the next input. The limit stops only the engine process the harness started. It does not promise to stop that process's children or to keep a full log. It cannot be combined with `--capture-policy`. The harness does not use `--capped-session`; each engine call gets `--json-evidence bounded --brief none`. Save available diagnostics through the authorized task's checkpoint policy.

Harness exit 0 means no attempted row was `RUN_FAILED`; it can include `NEEDS_ANTISMASH`, while verified resume skips are not counted as attempted rows. Inspect registry, metrics, completion receipts and the exact package before reporting whole-set completion. A registry row alone is not a resume receipt; retain existing unbound packages and use a fresh reviewed output root/registry after a binding hold.

The staged harness does not pass `--master` to `run`, so it updates no master workbook. To keep the packages in a Strain Master, submit each `*_Complete_Package.zip` through the inbox; see [where Mamey outputs land](DATA_HOME.md#where-mamey-outputs-land). For one cross-strain table, run `python mamey_run.py cohort-assemble --runs-dir <out> --out <out>/COHORT_MASTER.csv`.

The deliverable checker requires reported statuses/reasons and certain gold text/count fields, but does not open artifact paths, compare checksums, bind counts to the package, require unique rows or enforce the batch-size policy above. Its default mode is `standard`; pass `--mode gold` explicitly for the gold text checks. It rejects JUDGMENT_PENDING but does not independently validate every other reported gold state. A missing standing-constraint line is not itself rejected. Preserve those gaps as independent checks; a zero exit cannot certify the suite's content, profile compliance or scientific validity. See [deliverable contract](DELIVERABLE_CONTRACT.md) and [the manifest template](DELIVERABLE_MANIFEST_TEMPLATE.md).

Small sample size alone does not justify discarding an authorized per-strain deliverable. Runtime, available evidence and user scope still determine what can actually be completed. State unresolved evidence and output holds honestly; no policy here grants new experimental, online, publication or release authority.
