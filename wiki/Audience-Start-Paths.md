# Audience Start Paths

*Current to bundle v9.7.405 · engine Mamey 1.9.145. Authored by Codex (Wiki Revision 03, 2026-08-31) against v9.7.395; admitted to the bundle wiki at v9.7.405 by the Claude Code patch lane after a currency pass. Documentation only — confers no scientific, release, or publication authority; class-level hypotheses, judgment deferred.*


Choose the path that matches the object in front of you. All commands assume the current directory is the extracted Sapote–Mamey bundle root and use the bundle-local launcher, `python mamey_run.py`, so an older installed copy cannot shadow the bundle.

## Choose your path

| You are… | Start with | Stop point | Continue with |
|---|---|---|---|
| Running Sapote–Mamey for the first time | `doctor`, then `inspect` on one antiSMASH ZIP | A validated package with a readable manifest and no blocking gate failure | [Researcher Recipes: first successful run](Researcher-Recipes.md#recipe-1-first-successful-run) |
| Receiving or reviewing an existing package | `validate`, then `explain` | The package status, checksum state, issues, and recovery state are understood | [Researcher Recipes: validate a package](Researcher-Recipes.md#recipe-4-validate-a-package) |
| Processing a small, already-governed set of inputs | `inspect` each ZIP, then `run --strains` | Every per-strain result is checked separately and `HANDBACK.json` names the sealed deliverables | [Researcher Recipes: small batch](Researcher-Recipes.md#recipe-3-small-batch-of-up-to-about-three-strains) |
| Beginning post-seal interpretation or figures | Revalidate the package, then inventory evidence or preflight figure inputs | A typed availability/refusal state is recorded before authoring or rendering | [Researcher Recipes: Mode B](Researcher-Recipes.md#recipe-5-post-seal-mode-b-start) or [Figure Factory](Researcher-Recipes.md#recipe-6-figure-factory-next-preflight-and-refusal) |

## Path A — first-time analyst

You need one successful, understandable extraction before adding optional tools or post-seal interpretation.

1. Run `doctor` without network probes.
2. Run `inspect` on one raw antiSMASH output ZIP.
3. Run gold mode with explicit taxonomy, source, and provenance metadata.
4. Validate the unpacked package directory.
5. Use `explain` to read the package summary.

Proceed only when there are no blocking failures. Warnings about optional libraries, companion tools, or external datasets describe unavailable capabilities; they are not biological negatives.

## Path B — package recipient or reviewer

Do not infer package health from a ZIP filename, a spreadsheet, or a prior message.

1. Work from an unpacked package directory.
2. Read `manifest.json`, `checksums_sha256.txt`, `gate_validation.json`, and `package_status.json` when present.
3. Run `validate` and record both validator status and package recovery status.
4. Run `explain` only after validation is understood.
5. If continuing work, run `resume --json` and `workflow --json` with an additive ledger output path.

`MAMEY_COMPLETE`, `RECOVERY_VALIDATED`, `RECOVERY_NEEDED`, and `PARTIAL_FAILED` are different package states. A recovered package may validate while still retaining a recovery history.

## Path C — small-batch operator

Use the batch path only for a small set whose identities and metadata have already been checked. The CLI recommends up to about three ZIPs.

1. Inspect every ZIP independently.
2. Align pipe-separated taxonomy, source, and provenance values to the ZIP order.
3. Run `run --strains` with a shared output root and, when needed, a master workbook.
4. Read every per-strain status; a batch summary does not collapse failures into one pass.
5. Use `HANDBACK.json` to locate the sealed per-strain package ZIPs.

Cross-strain tables and figures are additive outputs. They do not prove that the inputs are biologically comparable or that metadata, antiSMASH profiles, evidence channels, and denominators are harmonized.

## Path D — post-seal researcher

Post-seal tools consume an already sealed package; they do not repair a failed extraction.

- For Mode B, create or supply a normalized inventory with the complete locus identity, run `modeb-availability`, inspect writing and promotion gates, and only then emit native Mode B top-lead material.
- For figures, verify the required optional dependencies and content-addressed inputs before running the renderer.
- For a resumed project, run `resume` and `workflow` to reconstruct progress from package artifacts and receipts.

Generated Mode B material, evidence-availability manifests, and figure receipts remain mechanical or visualization outputs. They do not establish compound identity, production, activity, novelty, causal phenotype linkage, experimental adjudication, owner acceptance, release, or publication readiness.

## Rules shared by every path

- Display every individual locus as `strain / full node-or-contig / region / BGC alias`. If any component is missing, hold the item rather than guessing.
- Keep evidence channels separate. NCBI nr, ClusteredNR, local Swiss-Prot, MIBiG, ClusterBlast, BiG-SCAPE, domains, cohort evidence, and literature do not substitute for one another.
- Treat missing or unbound evidence as a workflow state, never as biological absence.
- Read the package manifest before convenient derived views.
- Keep post-seal output additive and receipt-bound.
- Treat checksums, validation, and structural gates as bounded engineering evidence, not scientific or release authority.
