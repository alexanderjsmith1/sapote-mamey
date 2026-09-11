# Volume VII — Operations, Release & Provenance

> **Currency scope:** This volume retains its historical edition and review stamps. Only the checks listed in the [currency record](Encyclopedia-Currency.md) have been refreshed for the current candidate. Other constants, numerical claims, literature interpretations, and worked-run results have not been comprehensively revalidated. A newer bundle does not make those older observations current.

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (the guard patterns, the derive/resolve release functions and their PUBLIC-refused asymmetry, the four-tier make_public_tier.sh, and the version single-source-of-truth all re-verified against the running release machinery — including a live AS-XXX guard-refusal check) · 2026-06-16*
*Chapters VII.1–VII.9. The operations manual: how releases are classified, cut, verified, versioned, handed off,
and tailored. Grounded in the running engine of this edition.*

------------------------------------------------------------------------

## §VII.1 · Release classes and the leak guard

Every strain resolves to one of two release classes, and the boundary is a **hard guard** enforced in code
(`dedup_and_guard.py`), not a convention. <span class="tag t-engine">\[engine\]</span>

| Pattern | Regex | Class |
|----|----|----|
| `AS_PATTERN` | `\bAS-?\d{2,4}\b` | PRIVATE (unpublished) |
| `AJS_PATTERN` | `\bAJS-?\d{2,4}\b` | PRIVATE (unpublished) |
| `PENDING_PATTERN` | `\bPENDING\b` (case-insensitive) | PRIVATE (placeholder) |
| `PUBLIC_PATTERN` | `^(SID\d+\|PSEUDO\|AGLAU\|ACITR\|AGRAE\|MHUMI\|SPHIL\|SCLAV\|SDROZ)$` | PUBLIC (cleared) |

`derive_release(strain, private_registry)` is **fail-safe to PRIVATE**: it returns PUBLIC only when the strain
matches `PUBLIC_PATTERN` *and* trips no private guard; an AS/AJS/PENDING hit or a registry member is PRIVATE; an
**unrecognized** shape returns PRIVATE so an unknown identifier can never leak. <span class="tag t-engine">\[engine\]</span> (`dedup_and_guard.py:30`)

Two corrections this edition pinned (→ Vol I §I.7, the poll's CRIT-2): **WW- is *not* a private pattern** — it is
the public GenBank WGS prefix of public SID strains' contigs (SID-XXX→WWKG…), so it is deliberately absent from the
guard. And a public SID strain carrying a WW- accession is PUBLIC by `PUBLIC_PATTERN` (it matches `SID\d+`); the
accession is a contig label, not the strain's release class.

## §VII.2 · The `--release` operator override and its asymmetry

`resolve_release(strain, override, private_registry) → (release, refused)` governs operator intent. The asymmetry
is the load-bearing safety fact: <span class="tag t-engine">\[engine\]</span> (`dedup_and_guard.py:47`)

| Override | Strain shape | Result |
|----|----|----|
| `None` | any | `derive_release` (fail-safe PRIVATE) |
| `PRIVATE` | any | PRIVATE, `refused=False` (always honored — strictly more conservative) |
| `PUBLIC` | unrecognized (named genome / NCBI accession) | PUBLIC, `refused=False` (operator may open a public genome) |
| `PUBLIC` | trips AS/AJS/PENDING/registry guard | **PRIVATE, `refused=True`** (the leak guard is **not** operator-bypassable) |

The function returns the `refused` boolean so the caller can warn loudly when an operator's PUBLIC request was
overridden. The rule in one line: *an operator can open a public genome; no one can open an embargoed one by flag.*

## §VII.3 · The four-tier cut and the package/tier file map

A working tree is never shipped directly — a raw `git push` would leak AS identifiers embedded in code comments,
docs, and board files. `tools/make_public_tier.sh` is the **only** sanctioned way to cut a release; it stages a
copy, strips by tier, runs the in-tier audit, and refuses (non-zero exit) on any leak. `BUILD_STAMP` env stamps
the build. <span class="tag t-engine">\[engine\]</span>

| Tier | Command | Keeps | Strips | Audited |
|----|----|----|----|----|
| **CODE** | `make_public_tier.sh code` | engine + tests + docs (data-free) | `private/`, `cohort/`, `merged_cohort/`, `data/`, banks | 0 AS leaks |
| **CODE-analysis-free (clean)** | `… clean` | code tier | \+ worked strain-by-strain outputs; **anonymizes** SID####→SID-XXX | 0 AS leaks, 0 bare SID#### |
| **SID-public (sid)** | `… sid` | code + **SID banks** | `private/` | 0 AS leaks |
| **MERGED (merged)** | `… merged` | **everything incl. `private/` + AS IDs** | nothing | PRIVATE scaffold (not shippable public) |

Exit 0 means clean; for `code`/`clean`/`sid` it also means the leak audit found zero unpublished identifiers.
Only the `clean` tier anonymizes SID####; the `sid` tier keeps real SID#### (they are public).

**What the script actually does, step by step.** The tiers differ only in their strip list; the stage-copy, the
shared `strip_internal` helper, the self-stamp, and the audit are common. <span class="tag t-engine">\[engine\]</span>

1.  **Stage.** Copy the working tree to a scratch `STAGE` dir (the source tree is never mutated).
2.  **Strip by tier** (the literal removals):
    - `clean` — `rm -rf private/ cohort/ merged_cohort/ data/ release2_source_library/ docs/legacy/ offline_deps/`; then `strip_internal`; then `rm -rf deliverables/{deep_dives,analyses,reports} examples/ figures/` and `rm -f deliverables/DLV_EXAMPLES.md deliverables/HIVE_Board.csv`; then anonymize `SID####→SID-XXX`.
    - `sid` — `rm -rf private/ merged_cohort/ docs/legacy/`; then `strip_internal` (keeps `cohort/`, the SID data banks, but removes internal working docs).
    - `code` — the data-free strip (`private/`, `cohort/`, `merged_cohort/`, `data/`, banks).
    - `merged` — `: ;` (a deliberate no-op: keep everything, including `private/` and real AS IDs).
    - any other tier name → `exit 2` (fail-closed on an unknown tier).
3.  **Self-stamp the manifest.** If a real `VERSION` is supplied, rewrite `RELEASE_MANIFEST.md` to that version
    in-place — this is the guard against the historical "v9.5.5-style" version drift where the manifest and the
    bundle disagreed; the cut *cannot* ship a manifest that lies about its version.
4.  **Audit in-tier.** Run the leak audit inside `STAGE`; a single unpublished identifier is a non-zero exit and
    no artifact is produced.

The design intent: the only difference between a safe public cut and a catastrophic leak is one argument
(`code`/`clean`/`sid`/`merged`), and every path that isn't `merged` ends at an audit that fails closed.

**Package file map.** The full, current `Complete_Package` file map — numbered by pipeline stage, including the `2b` crosswalk, the `4B`/`4c` rescue and AB/AF lead boards, the `5`/`5b` workbook + worklist, the `6`/`7` checklists, `figures/`, and `locus_maps/` — is maintained in **§II.7** and is not duplicated here; the four-tier cut operates on that package unchanged. What the tiers strip is the *repository* material around it (`private/`, `cohort/`, `merged_cohort/`, banks), never the per-strain package’s internal structure. <span class="tag t-engine">\[engine\]</span>

## §VII.4 · Byte-parity and the per-tier gate

Cutting four tiers from one tree creates a risk the discipline closes: that a fix lands in one tier and not the
others. Two checks enforce consistency. <span class="tag t-engine">\[engine\]</span>

- **Byte-parity.** Every engine file shared across tiers must be byte-identical between CODE / SID / MERGED;
  verified with `sha256sum` across the cut tiers. A diff on a shared *code* file across these three is a cut error,
  not a feature. The analysis-free tier is the one principled exception: it legitimately differs from the trio by
  **comment-only scrubs** (e.g. `render_brief.py` `PENDING-XXX→XXX`; `scoring.py:96/282` `SID-XXX→SID-XXX`), which
  are allowed and logged — *not* code changes. The discipline a per-file parity manifest enforces (→ §VIII.3) is the
  distinction itself: **code diffs must be zero; scrubbed-comment diffs are permitted but enumerated**, so an
  audit that reports "one mismatch" without classifying it is undercounting (an error two prior audits made —
  PC-08).
- **Per-tier pytest + leak audit, run not assumed.** The full suite runs *inside each cut tier* (not just the
  working tree), and the leak audit re-scans the cut. A multi-tier delivery discloses each tier's
  pass/fail and leak status explicitly; a fix is never assumed to have propagated.

This is why a multi-tier release report states, per tier, the test count and the leak-audit result — the
disclosure is the deliverable, not an afterthought.

## §VII.5 · The manifest, provenance, and the version single-source-of-truth

Provenance is carried in the **manifest** (`manifest.json`): the release class, `workflow_version` (the bundle
string), `analysis_date`, source, taxonomy, and the strain identity fields. A figure or report restates the same
edition stamp so any artifact traces to the engine that made it (→ §VI.3). <span class="tag t-engine">\[engine\]</span>

Version is a **single source of truth** propagated, never retyped: <span class="tag t-engine">\[engine\]</span> (`tools/sync_version.py`)

| Fact | Source of truth | Restated in |
|----|----|----|
| **engine** version (Mamey; what `pip install` produces) | `pyproject.toml [project].version` | `mamey/__init__.__version__`, the standalone-contract test |
| **bundle** version (the curated release) | `pyproject.toml [tool.sapote].bundle_version` | `BUILD_STAMP.txt`, the newest `CHANGELOG.md` header |

`python3 tools/sync_version.py` rewrites the restated files in place; `--check` exits non-zero if anything is out
of sync (no writes). A version-string drift fails the suite rather than shipping — the standalone contract asserts
the running `__version__` matches the declared engine version.

## §VII.6 · The handoff format and the recut/audit loop

Work moves between chats and sessions under a standardized **handoff** (`sapote-mamey-handoff/v0.2`): a manifest
block carrying the bundle state, a `release` class, a `superseded[]` list (so a re-stamped artifact names what it
replaces), and an `output_feedback` channel for front-facing-document notes. The leak rule extends to the handoff
itself — an unpublished identifier may not appear even in a feedback example. <span class="tag t-engine">\[engine/spec\]</span>

The **recut/audit loop** is the engine's correctness engine: each release is independently audited (an audit chat
re-verifies every <span class="tag t-engine">`[engine]`</span> claim against the running code), findings are logged, and the next cut closes them.
A provenance honesty rule rides along — a metric is labelled **vendor-reported** (taken from antiSMASH/source) vs
**reproduced** (recomputed by Mamey), never blurred. The encyclopedia poll that produced this edition's
corrections (the AB-diagnostic count, the CCTT family roster, the \#28 real-data caveat) is one turn of that loop.

**The cadence, concretely.** A normal turn runs in a fixed order, and each stage has a fail-closed gate: <span class="tag t-engine">\[engine/spec\]</span>

1.  **Patch** against the working tree (one incremental, verifiable change — never a rewrite), with a new test that
    fails before and passes after.
2.  **Suite.** Run the full pytest suite (currently ~1404 passed / ~91 skipped at v9.7.91); a red suite blocks the cut. The
    version-sync check (`sync_version.py --check`, §VII.5) runs here too — a version-string drift fails rather than
    ships.
3.  **Conservation audit.** Run the boundary audit (`boundary_audit.py`, §II.7) on every strain touched — the
    SOURCE→PACKAGE check that no found evidence was lost and no recorded exclusion went unhonoured. This is the
    loop's conservation check: it is what makes "nothing dropped silently" an enforced invariant across recuts, not
    a per-release hope.
4.  **Cut + in-tier leak audit.** `make_public_tier.sh` per tier (§VII.3), each ending at a leak audit that fails
    closed on a single unpublished identifier.
5.  **Per-tier verification.** Run pytest *inside each cut tier* — propagation is never assumed (a fix that landed
    in CODE may be absent in a stripped tier); the multi-tier delivery disclosure states, per tier, that the fix
    landed.
6.  **Handoff + log.** Emit the handoff manifest (above), record findings, and open the next turn against them.

The discipline is that no single step is trusted to have covered for another: the suite does not excuse the
conservation audit, the conservation audit does not excuse the per-tier leak audit, and a green CODE tier does not
excuse re-running the suite inside the stripped tiers. The loop is slow on purpose — correctness here is an
invariant the project re-earns every cut.

## §VII.7 · Customizing Sapote–Mamey to your settings

Sapote–Mamey is calibrated for actinomycete natural-product discovery, but the calibration is **legible and
editable**. Most tuning today is done by editing named module constants (a settings *file* is a future
convenience, not yet built), so customization is a deliberate, reviewable change — and a good thing to do *with
Claude in the loop*, which is the intended workflow: describe the goal, and Claude can locate the exact constant,
make the change, and run the suite to show nothing else moved. <span class="tag t-engine">\[engine\]</span>

The tunable surface: <span class="tag t-engine">\[engine\]</span>

| Setting | Where | Default | Effect of changing |
|----|----|----|----|
| AB / AF / novelty keyword weights | `scoring.py` `AB_KEYWORDS` / `AF_KEYWORDS` / `NOVELTY_KEYWORDS` | e.g. carbapenem 18, hsaf 20, enediyne 18 | re-weights how a class moves an axis (→ §V.1) |
| Diagnostic bonus | `scoring.py` `DIAGNOSTIC_BONUS` | 25 | how much a corroborated diagnostic trigger lifts its axis |
| AB / AF diagnostic sets | `scoring.py` `AB_DIAGNOSTIC_TRIGGERS` (8) / `AF_DIAGNOSTIC_TRIGGERS` (3) | LAN/LASSO/THA/PHO/AMC/BLA/GPA/BLT · NUC/PTM/PYE | which triggers are strong enough to floor a tier |
| Lead-tier thresholds | `scoring.py:455` | Exceptional 85 / High 70 / Medium 50 | the cutoffs on `max(AB,AF,novelty)` |
| Corrected-count weights | `assembly.py:29` | Interior 1 · Edge ½ · Full-contig ¼ | how fragmentation discounts the count |
| Assembly-tier cutoffs | `assembly.py:31` | GOOD 70 / MODERATE 45 / POOR 20 | the interior-% bands |
| RiPP-fragment cap length | `scoring.py` `RIPP_FRAGMENT_MAX_KB` | 8.0 | the size below which a precursor-less RiPP is capped at Inventory |
| Standing rules (permanent downgrades) | `scoring.py` `_RULE_FLAG` / `standing_rule_for` | saccharide / NAPAA / hglE-KS-PREV-001 | which classes are excluded from corrected rank (→ §VIII.4) |
| CCTT triggers / markers | `source_scans.py` `CCTT_PATTERNS` + the registry (→ §VIII.3) | 18 families | the class-corroboration signatures |
| Edge penalty <span class="tag t-engine">removed v9.7.84</span> | `scoring.py` `edge_penalty` (returns 0) | Historical (≤1.9.84): Interior 0 · Edge 10 · Full-contig 18; now 0 (confidence grade carries truncation) | how hard truncation pulls the axes down (→ §III.3) |
| Penalty multipliers | `scoring.py` | AB/AF × 0.35 · novelty × 0.2 | how much truncation costs a bioactivity claim vs a novelty one |
| RG-GMCI rescue | `scoring.py` `rescue_bonus` | 8 (HIGH) · 4 (MODERATE) | the lift + penalty-reduction a cross-contig-rescued fragment gets |
| Novelty corrections | `scoring.py` (novelty corrections) | KCB \>10000 −15 · missing/unknown KCB no credit · RiQ \<0.5 +10 | how known-similarity and rarity move novelty |
| Tier-1 floor exclusions | `scoring.py` `TIER1_FLOOR_EXCLUDED_PREFIXES` | `T43-HAL_`, `T43-XHAL_` | which promiscuous triggers do *not* floor a tier (→ §V.2) |
| Primary-metab over-call set | `scoring.py` `WEAK_OVERCALL_CLASSES` | 14 weak labels; see `WEAK_OVERCALL_CLASSES` for the exact set | which "class" labels are weak enough that a housekeeping core triggers the primary-metab guard |
| Boundary flank | `parsers.py:193` `_edge_status(flank_bp=5000)` | 5,000 bp | how close to a contig end counts as Edge (→ §II.2) |
| Coupling flank | `source_scans.py:317` `bgc_coupling(flank=10000)` | 10,000 bp | how near a scan hit must be to couple to a BGC |
| TFBS window | `source_scans.py:470` `scan_tfbs(upstream_bp=300)` | 300 bp | the upstream window the regulator-motif scan reads |
| Run options | CLI: `--release`, `--mode`, `--json-evidence`, `--brief`, `--taxonomy`, `--source` | — | per-run behavior, not a recalibration |

The tunables fall into four kinds, and the distinction matters: **calibration weights** (keyword tables, the
diagnostic bonus) change *how strongly* a signal scores; **geometric thresholds** (the tier cutoffs, edge penalty,
the flanks) change *where the lines are drawn*; **guard sets** (the diagnostic/floor-exclusion/over-call lists)
change *which signals are treated as load-bearing*; and **run options** change a single run, not the calibration.
A worked retune: to make the pipeline more antifungal-sensitive you would raise the relevant `AF_KEYWORDS` weights
and/or lower the Medium cutoff — both calibration, both reversible, both observable in a re-run; to instead make it
treat a new class as diagnostic you would add the trigger to `AF_DIAGNOSTIC_TRIGGERS`, which is a *guard-set*
change (it newly lets that class floor a tier) and so deserves more scrutiny. In every case the workflow is the
same: change the named constant, run the suite, and re-run a reference strain to see exactly what moved — a
calibration you cannot see move is one you cannot trust.

**Invariants that should not be loosened** (they are the project's epistemics, not preferences): the leak guard
(§VII.1–2); capacity-not-production language; KCB = similarity, not identity; the corroboration gate; the
extract-level bioactivity default (absence ≠ negative). Re-weighting a keyword is calibration; removing one of
these is changing what a claim *means* — Claude will flag the difference before making such an edit.

## §VII.8 · Bundle naming and a non-overlapping namespace *(framing — not finalized)*

A lab running its own strains and cohorts needs release identifiers that will never collide with another lab's, or
with the canonical bundle's own version line. This chapter is intentionally a **frame, not a fixed scheme** — the
right naming convention is a decision to make interactively with Claude against the lab's actual constraints. The
design goals a scheme should satisfy: <span class="tag t-concept">\[concept\]</span>

1.  **Non-overlap with the engine/bundle version.** A site bundle name must be distinguishable from the canonical
    `vMAJOR.MINOR.PATCH` engine/bundle line so a local build is never mistaken for an upstream release.
2.  **A site/owner prefix.** A short, stable namespace token (lab or project) so two sites' artifacts never collide
    on `bgc_uid`, package names, or handoff IDs.
3.  **Release-class legibility.** The name should not *defeat* the leak guard — i.e. a private cohort's identifier
    should still resolve PRIVATE under §VII.1 (or the guard's patterns extended to cover the new namespace, with
    the parity tests updated, → §VIII.3).
4.  **Provenance-stable.** Once assigned, an identifier should be immutable and carried in the manifest, with any
    re-stamp recorded via `superseded[]` (§VII.6).

When the scheme is chosen, it lands as: a documented convention here, optional new patterns in `dedup_and_guard.py`
(with parity tests), and a manifest field — a small, testable change. Until then, the canonical conventions
(AS/AJS/PENDING private, SID-public, named genomes public) stand.

------------------------------------------------------------------------

## §VII.9 · Top-level archive rule and Mamey-first cohort workflow <span class="tag t-engine">\[engine\]</span>

**Top-level archive rule.** Every multi-strain delivery must be organised into exactly two
top-level ZIPs:

    PROJECT_ALL_DATA_<N>strains_v<version>_<date>.zip
    PROJECT_PATCH_ONLY_All_Patch_Info_v<version>_<date>.zip

The **ALL_DATA** archive contains sealed per-strain packages, the master workbook, figures,
reports, manifests, and any later strain-specific Mode B ZIPs. The **PATCH_ONLY** archive
contains patch cards, diffs, acceptance checks, documentation suggestions, and developer notes.
These two classes must not be mixed. A delivery with ambiguous sibling ZIPs required for
completeness is an incomplete delivery.

**Mamey-first cohort workflow.** For a cohort, run Mamey extraction across all strains before
beginning deep Sapote Mode B interpretation. Mamey produces the deterministic substrate —
sealed per-strain packages, node-first locus labels, raw and corrected BGC counts, CNBU when
available, lead boards, special-review buckets (→ §VI.10), RG-GMCI pairs, and workbook-ready
rows. Once all strains are banked, use the master workbook to select Mode B targets. Running
full Mode B on every strain before seeing the cohort pattern wastes judgment time on
low-priority loci. <span class="tag t-engine">\[engine\]</span>

**Mode B strain-specific ZIPs.** After Mamey-first cohort triage, only selected priority strains
need expanded Mode B. Each selected strain should receive a strain-specific Mode B ZIP:

    <strain>_MODE_B_ALL_DATA_<version>_<date>.zip

That ZIP must contain: the full Mode B report, claim ledger, source CSVs, figures, figure
manifest, literature checklist, manual follow-up list, and validation status. The next
top-level ALL_DATA archive must include all strain-specific Mode B ZIPs produced since the
previous delivery. <span class="tag t-judgment">\[judgment\]</span>

------------------------------------------------------------------------

*End of Volume VII. Next: Volume VIII — Reference & Apparatus (glossary, the KCB denominator apparatus, the
marker-catalog/registry-parity discipline, the standing-rules registry, version-history known-traps, and the
literature apparatus).*

</div>

<div id="vol8" class="section vol">
