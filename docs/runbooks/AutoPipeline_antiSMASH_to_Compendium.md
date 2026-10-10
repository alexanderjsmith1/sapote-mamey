# From an antiSMASH ZIP to a reviewed report

This file retains a historical v9.7.319 session plan below. It is not an automatic upload hook, a complete executable pipeline or evidence that its session-created scripts ship. `tools/check_dangling_refs.py` explicitly exempts `build_factsheet.py` and `build_handoff.py` as per-session glue; neither name was found as a shipped Python script. An exemption from a dangling-reference check does not implement that script.

For the current engine, start with [the master walkthrough](../MASTER_WALKTHROUGH.md) and [installation](../INSTALL.md). For authored cards, use [current Mode B](../MODEB_CURRENT50_V2_CONTRACT.md); for reports, use [post-seal readers](../POSTSEAL_READERS.md). The assistant must follow the user's current instruction and selected profile, not treat this historical plan as permission to execute every stage.

## Current bounded sequence

1. Inspect the supplied ZIP and record its path/hash, antiSMASH version, exact strain identity and available metadata. Ask for unresolved identity when required; do not normalize an identity by blindly stripping filename suffixes. Genus, host and assay context require their own sources.
2. Select the execution profile and fresh output root with the user. Gold is the engine mode. `--capped-session` forces briefs off, main JSON evidence off and a required workbook; it is not a universal process timeout or proof of full evidence. Explicitly choose deferred figures and optional reference completion according to available dependencies and the work order.
3. Run only the authorized route, retain command/manifest/issue receipts and validate its package. Interpret complete-with-issues, missing, truncated and held states as recorded. A validator pass does not finish Sapote interpretation.
4. Select exact loci for review using full strain / node-or-contig / region / BGC alias identities. Preserve source evidence; author the chosen contract and verify that profile. Templates, lead scores and serialised judgments do not independently establish function, activity or product identity.
5. Generate only the requested figures/reports in their documented output locations. Retain data/captions/source hashes and inspect rendered pages before claiming visual QA. A compendium needs its own explicit input roster, generator and acceptance check; this runbook supplies none.
6. Deliver the indexed outputs, evidence and unresolved holds. Preparing a handoff does not authorize messaging another chat, starting subagents or publishing results.

The old “permanent downgrades” list is not current source policy: for example, `mamey/data/rules_registry.json` marks NAPAA neutral/action none. Read the actual current rules/profile and preserve the selected denominator and version scope. The old compressed-ZIP-size scheduling threshold is session advice, separate from the full-mode guard on uncompressed JSON bytes. Historical biological pattern lists are hypotheses to inspect, not mandatory hits or adopted scientific conclusions.

## Historical session plan — original body retained

The following is dated source history and supplies no current execution or scientific authority.

---

# AutoPipeline: antiSMASH ZIP → Mamey → Handoff → Compendium

**Patch v1.0 · bundle Sapote–Mamey v9.7.319 · engine Mamey 1.9.98**
**· PRIVATE**

A runbook (not engine code) describing how a Claude session auto-runs the full
single-strain pipeline when an antiSMASH ZIP is uploaded. The engine pieces it
calls (`mamey_run.py`, `mamey/locus_map.py`, the locked locus palette, gold mode)
ship in this bundle; the session glue scripts (`build_factsheet.py`,
`build_handoff.py`, expansion/compendium generators) are created per-session.

See the Patch Chat record for the full step list. Summary of the 9 steps:
1. Identify strain ID (strip suffixes).
2. Mamey gold-mode extraction → package.
3. Build fact sheet (metadata lookup order: conversation → master list → PENDING).
4. Build Sapote handoff markdown (self-contained for a parallel chat).
5. Locus maps for top 3 AB + top 2 AF leads (locked palette, data-only PNG + CSV).
6. Mode B cards at lead-tier depth, standing rules applied before writing.
7. Domain expansions (EXPANSION = PKS/halogenase/etc; EXPANSION2 = sulphur/saccharide).
8. Assemble per-strain compendium.
9. Present outputs + plain-text summary.

Standing rules enforced throughout: capacity-not-production; KCB = similarity;
bioactivity extract-level; contig/node on every BGC; the permanent downgrades
(NAPAA, NI-siderophore, NRP-metallophore, hglE-KS/PREV-001, ectoine, PQQ);
enediyne = neutral [E-signal], no BSL-2 flag. Batch strains sequentially (memory);
large ZIPs (>50 MB) run alone. Genus never inferred from KCB.

Cross-strain pattern flags to check per strain: DUF692, ranthipeptide, AP_endonuc_2,
PQQ, HxlR, SnoaL_2, Asn_synthase+RRE, T3PKS chalcone synthase, Hemerythrin, SelO,
GlfT2, GlgE, LytR, Bac_transf.
