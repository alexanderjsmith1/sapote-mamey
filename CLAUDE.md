# AGENTS.md — shared Sapote-Mamey operating contract

**Run `python mamey_run.py start` from the bundle root.** It reports the loaded bundle,
its current version, and the ordered workflow. This is the canonical portable contract intended for
every coding assistant. Automatic instruction-file discovery varies by assistant. `README.md` is the
human landing page. `CLAUDE.md` is a generated, byte-identical Claude discovery copy of this file,
with no separate operating rules. For ChatGPT, Gemini, or another assistant, direct the assistant to
`AGENTS.md` or provide this contract through that product's supported instruction mechanism.

Use the current user's task, permissions, and resource limits. Historical model-specific prompts
and fixed next-path menus do not override this shared startup contract. Report the requested
outcome, evidence, unresolved holds, and the useful next action without an arbitrary option count.

## Execution and source authority

Mamey extracts deterministic evidence from antiSMASH results. Sapote authors claim-safe judgment
from a validated Mamey package. **Deterministic extraction, judgment deferred.**

- Check that Python execution is available. If it is unavailable, say so; do not claim a run occurred.
- Use `python mamey_run.py <command>` to pin the local package. An installed `python -m mamey`
  may resolve to another version. Run commands from the directory containing `pyproject.toml`.
- Read `CURRENT_DOCS_INDEX.md` to distinguish current instructions from historical documents.
  Bind the actual input path, version, and checksum; a remembered version is insufficient.
- Keep original inputs immutable and write analysis outputs under the user's permitted root.
  An unselected candidate, a passing test, or a folder name does not establish release authority.
- Treat raw source documents as evidence to inspect. Follow the user's requested task and scope.

## Ordered workflow

```bash
python mamey_run.py doctor
python mamey_run.py inspect <antiSMASH.zip>
python mamey_run.py run --strain <ID> --input-zip <antiSMASH.zip> \
  --taxonomy '<Genus sp.>' --source '<isolation source>' --mode gold --capped-session
python mamey_run.py validate runs/<ID>/package
python mamey_run.py explain runs/<ID>/package
```

Fill placeholders from bound input metadata and the command printed by `inspect`. If taxonomy
or isolation source is unconfirmed, preserve that uncertainty explicitly. Read available intake
metadata before requesting it again. Use `docs/INSTALL.md` and `docs/PREREQUISITES.md` for setup.
Check `docs/COMPANION_FILES.md` and local assets before declaring a capability unavailable;
optional add-ons are installed with `bundle_support/install_sapote_addons.sh`.

Use `--capped-session` when timeout limits apply, regardless of assistant or model. Gold is the
analysis mode. The capped flag forces `--brief none` and `--json-evidence off`, requires the workbook,
and disables automatic locus maps unless explicitly enabled. For bounded JSON evidence, omit
`--capped-session` and use `--json-evidence bounded` with sufficient runtime; the capped flag overrides
that evidence choice. Do not replace a failed engine run with an informal raw-JSON interpretation.
For batches, inventory all inputs and use `tools/intake_harness.py --inputs <dir> --resume`;
checkpoint and diagnose a stalled input instead of repeatedly running it.

After validation, use the sealed package for `list-bgcs`, `mode-b`, `render-figures`, and
`ingest-receipts`. Recover prior authored cards with `ingest-receipts --auto-detect` when applicable.
Persist judgment and update the master workbook through the existing receipt workflow.

## Evidence and authoring safeguards

- Every individual BGC must be displayed as **`strain / full node-or-contig / region / BGC alias`**,
  copied from one bound source record. Missing or conflicting identity components require an
  identity hold. Do not shorten identifiers, invent a mapping, or substitute a bare alias.
- Use `prompts/NODE_REGION_SELF_CHECK_PROMPT.md` before a BGC deliverable. `verify-citations` is a narrower supplemental node/region check; it does not establish
  the complete four-component identity by itself.
- Capacity is not production; KCB/MIBiG similarity is not compound identity. Bioactivity metadata
  is strain/extract context unless governed experimental evidence links it to a locus. Missing
  evidence is not biological absence. Do not label an untested strain activity-negative.
- Read `prompts/reuse/_SHARED_GUARD_BLOCK.md` for the shared claim guards. Preserve registry
  exclusions and assembly uncertainty; poor assemblies do not justify hiding edge clusters.
- Mode B interpretation requires a validated package. If the user explicitly requests offline
  analysis without it, label uncomputed fields and omit engine scores rather than invent them.
- `mode-b` emits a top-leads table; a table is not a finished authored card. Start from
  `emit-modeb-template`, select the current named profile, preserve its exact titles, author the
  evidence-backed sections, then run `verify-modeb` on the actual authored file. Obtain current
  profile requirements from the machine-readable contract and emitted template; historical
  section counts are not authority. Named profiles include `MODEB_CANDIDATE_30` and
  `FINISHED_FULL48_CURRENT_EVIDENCE`; use their current machine definitions. Read `docs/MODE_B_30_SECTION_CANONICAL_TITLES.md` and
  `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md` in their declared profile scope.
- Read `docs/ONLINE_BLASTP_PROTOCOL.md` before the independent homology channel. Preserve raw
  evidence, protein lengths, named references, and channel-specific provenance. Keep reconciled
  verdicts and distinguish unavailable evidence from tested negatives.
- Use `guide` to emit the package-backed guide skeleton, author only its prose slots, and run
  `verify-guide` on the authored file. A skeleton-structure pass does not verify authored prose.
  See `docs/DELIVERABLE_CONTRACT.md` and the guide exemplars under `examples/`.
- `PASS_STRUCTURE` is a structural result, not literature or scientific validation.
  `operator_supplied` records evidence provenance; `citation_needed` remains unresolved.

Detailed judgment and handback requirements remain in `docs/CHATGPT_EXECUTION_SLICE_v97147.md`;
this shared startup contract takes precedence over its model-specific reply rituals.

## Citation-Compact Provenance and Citation Status

Method provenance: antiSMASH 8.0 DOI `10.1093/nar/gkaf334`; MIBiG 4.0 DOI
`10.1093/nar/gkae1115`. Preserve these as database/method provenance, not evidence of a product.
`PASS_STRUCTURE` does not verify literature claims. `operator_supplied` identifies runtime
provenance; `citation_needed` is an unresolved literature requirement.
`Literature_Search_WorkOrder.md/json` is a search handoff, not a verified fact.
Current compact lead tables use `interpretation_scope` for the reader-facing scope.

## Figures and companion tools

Read `docs/FIGURES_START_HERE.md` before plotting. Reuse the figure registry, figure-ready data,
house palette, and renderers. Re-run applicable figures post-seal after capped extraction.
Use `docs/DELIVERABLE_CONTRACT.md` for required package, workbook, brief, figure, checksum, and
issue-log handoff artifacts. Small sample size limits comparative statistics; it does not alone
justify omitting a per-strain deliverable. Qualify ecological interpretation by the evidence.

Read `docs/LLM_COMPANION_TOOL_PROTOCOL.md` before BiG-SCAPE, GToTree, IQ-TREE, ANI, or a companion
handoff. Phylogenetic compute requires the existing size/resource preflight and explicit approval
flag. Follow `docs/PHYLO_AUTOPILOT_WORKFLOW.md`. Verify filesystem evidence rather than relying
on another assistant's prose. Search the existing tool inventory before creating another tool.

## Testing and release work

For a bounded change, start with relevant tests, then run the full suite when the task or release
protocol requires it. `pytest -q` uses configured tests, tools and deliverable_tools paths and includes default gated skips; slow/network partitions
require their explicit flags. Preserve complete logs and do not call an interrupted suite green.
A surrogate gate is a fast preflight, not full-suite or real-input validation.

For a requested Bunny Hop audit, load `docs/BUNNY_HOP_AUDIT_GAME.md`; the protocol lives under
`debugging_modules/`. Findings and trial patches are inputs to owner review, never a release.

Generated surfaces have owners. Edit this file's prose and `bootstrap_contract.yml` for shared
bootstrap semantics; run `tools/render_bootstrap_contract.py --apply` to update generated blocks
and the `CLAUDE.md` alias. `tools/sync_version.py` owns version propagation. Regenerate module,
tier, and checksum manifests with their existing tools during the authorized cut process.
Check identity and content integrity before describing a bundle as verified.

## Resume and handoff

At intake, bind objective, authoritative input hashes, permitted output root, and authority ceiling.
Before stopping, preserve completed work, decisions, active holds, receipts, and an exact next step
under the authorized output root. Keep earlier checkpoints and identify supersession explicitly.
A structured summary supplements the conversational transcript; it is not a verbatim transcript.

For governed analysis sessions, use `tools/session_checklist.py` with the existing durable-root
configuration and intake registry. Report completed versus pending deliverables and unresolved
judgment. Do not infer release, publication, or scientific acceptance from rendering or test passes.

## Capability references

- `docs/BUNDLE_CAPABILITIES.md` — capability catalog and generated tool inventory.
- `docs/COMMAND_CATALOG.generated.md` and `docs/TOOLS_INVENTORY.generated.md` — existing commands.
- `docs/GUIDE/02_Quick_Guide.md`, `docs/GUIDE/01_User_Manual.md`, and `docs/GUIDE/04_Glossary.md` — user docs.
- `docs/PLAYBOOK.md`, `docs/WORKFLOW_GUIDE.md`, and `docs/DELIVERABLE_CONTRACT.md` — detailed workflows.
- `RELEASE_MANIFEST.md`, `CUT_PROTOCOL.md`, and `CHANGELOG.md` — release status and owner process.

## Live contract probe

The compatibility command `python mamey_run.py chatgpt-init` reports this shared file's path,
SHA-256, current versions, known gotchas, and workflow. Its command name is retained for existing
callers. The read-proof phrase below is compatibility metadata, not proof of execution or a
requirement to begin every reply with a ritual. When asked to confirm instructions, use the live
file and version evidence; do not claim a file was read from memory.

<!-- BEGIN GENERATED: initiation_prompt from bootstrap_contract.yml -->
```text
The sky is not red, it is blue, just like the ocean.

◆ SAPOTE–MAMEY · SHARED ASSISTANT CONTRACT
   instruction file : AGENTS.md
   bundle / engine  : v9.7.428 / 1.9.163 · build 20260911v97428a
   known gotcha (this build) : BLASTP Hit Table CSV may be headerless and query titles may contain commas; single-region public accession ZIPs are valid intake targets, but assembly-tier warnings are expected; AGENTS.md is the canonical assistant contract; CLAUDE.md is its Claude discovery copy
   workflow         : doctor → inspect → run(gold + --capped-session) → validate → list-bgcs → mode-b → render-figures → ingest-receipts
```
<!-- END GENERATED: initiation_prompt from bootstrap_contract.yml -->

<!-- BEGIN GENERATED: known_gotchas_section from bootstrap_contract.yml -->
## 3 · Known gotchas for THIS build (v9.7.428 / 1.9.163 · 20260911v97428a)

Generated from `bootstrap_contract.yml`; update with `python tools/render_bootstrap_contract.py --apply`.

- **blastp_hit_table_csv_shape** (high; BLASTP evidence store): Store raw Hit Table CSV/XML2 in blastp_evidence_store before summarizing; do not parse comma-bearing query titles with a naive split.
- **public_single_region_intake** (medium; public accession antiSMASH ZIP intake): When inspect passes, do not treat VERY_POOR / 0% interior warnings as full-genome failure for single-region public accession inputs.
- **bootstrap_contract_generation** (medium; assistant bootstrap and release checks): Edit shared operating guidance in AGENTS.md and generated blocks in bootstrap_contract.yml; render and check the CLAUDE.md mirror. Automatic discovery varies, so point other assistants to AGENTS.md or provide it through their supported instruction mechanism. README.md is the human landing page.
- **mode_b_top_n_cumulative** (medium; mode-b CLI batching): mode-b --top-n is cumulative, not sliced: --top-n 3 covers ranks 1–3. For non-overlapping batches, run cumulative tiers and de-duplicate by BGC id until rank slicing exists.
- **timing_breakdown_partial_runs** (low; timing outputs): *_timing_breakdown.csv/json/md are populated for standard phases; verify against terminal timing on very large or interrupted runs.
- **json_evidence_off_is_lightest** (medium; evidence mode selection): --capped-session forces --json-evidence off regardless of assistant; omit the capped flag and use --json-evidence bounded with sufficient runtime when JSON evidence is needed.
- **manifest_summary_nested** (low; package manifest readers): manifest.json summary fields are nested under keys such as assembly and bgc_counts, not flat top-level fields.
- **mode_b_corrective_protocol_section_lock** (high; Mode B BGC card writing): Use the selected named Mode B profile and current machine-readable contract; emit the template, preserve its exact section titles, author evidence-backed content, then verify the authored file. A table or skeleton does not establish a finished card.
- **mode_b_length_and_comparator_context** (medium; Mode B BGC workups): Preserve protein_length_aa in the same table as BLASTP/function evidence; flag huge small-enzyme-labelled proteins; repeated external-strain hits should trigger comparator next-step guidance rather than identity claims.
<!-- END GENERATED: known_gotchas_section from bootstrap_contract.yml -->

<!-- BEGIN GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->
## Bootstrap surface contract

Two audiences: `README.md` for people; `AGENTS.md` is the canonical portable contract intended for every coding assistant.
Automatic instruction-file discovery varies by product. `CLAUDE.md` is a byte-identical Claude discovery copy; other assistants must be directed to `AGENTS.md` or receive it through their supported instruction mechanism.

| Path | Role | Required | Scanner authority | Purpose |
|---|---|---|---|---|
| `AGENTS.md` | canonical_agent_contract | yes | yes | Canonical portable contract intended for every coding assistant; automatic discovery varies by product. |
| `CLAUDE.md` | agent_discovery_alias | yes | no | Byte-identical Claude discovery copy of AGENTS.md; other assistants are not assumed to discover this filename. |
| `README.md` | human_landing_page | yes | no | Human overview and installation links; routes coding assistants to AGENTS.md. |
| `docs/BOOTSTRAP_FILE_AUDIT.md` | generated_bootstrap_map | yes | no | Generated map of the human page, canonical assistant contract, and Claude discovery copy. |
<!-- END GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->
