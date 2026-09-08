# Lab Quest: governed optional local interface

Lab Quest is a local accessibility and navigation layer over one explicitly configured portable
Mamey code tier. It is not a second biological engine, a workspace-discovery tool, or scientific
authority.

**Status (v9.7.405 candidate):** the library (`mamey/lab_quest.py`), workflow registry
(`mamey/lab_quest_registry.py`), the Streamlit app (`mamey/lab_quest_app.py`), the shared
exact-locus display contract (`mamey/exact_identity.py`), and the portfolio/privacy/catalog layer
(`mamey/portfolio_config.py`, `mamey/project_catalog.py`) are landed and tested. The `lab-quest`
subcommand is registered in `mamey/cli.py` — `python mamey_run.py lab-quest ...` is a recognized
subcommand.

## Install and launch

Install the optional interface dependencies from the extracted bundle, then bind the exact code
tier and expected versions deliberately:

```bash
pip install 'mamey[labquest]'
python mamey_run.py lab-quest \
  --project-root /path/to/project \
  --code-tier /path/to/extracted/sapote-mamey \
  --expect-bundle-version <this bundle's BUNDLE_VERSION> \
  --expect-engine-version <this bundle's mamey.__version__> \
  --headless
```

The launcher refuses to start unless both `--project-root` and `--code-tier` are explicitly
supplied. It then requires the configured code tier to contain `mamey_run.py`, `pyproject.toml`,
and `mamey/__init__.py`, with bundle and engine versions that agree with each other and with the
expected values. Neither the command-line launcher nor the app accepts an unset project-root
binding or falls back to the launch directory. The launcher uses no glob, "newest version," or
personal-workspace search. The local server binds to `127.0.0.1` and disables Streamlit telemetry.

Use `--verify-only` with the same required bindings to validate the portable source and write an
engine-binding receipt without installing Streamlit or launching the interface. This is a local
provenance check only, not a package, scientific, owner-review, release, or publication approval.

## Six receipt-backed stations

1. **Input** stages a contained antiSMASH ZIP and writes its hash-bound receipt.
2. **Extraction** invokes only the bound code tier's `mamey_run.py run` command.
3. **Package validation** validates the selected package, binds its current manifest hash, and
   fails if an exact locus cannot be formed.
4. **BLASTP status** runs the supported availability/status command. It records a workflow state,
   not homology findings.
5. **Mode B skeleton** invokes the supported deterministic skeleton emitter
   (`emit-strain-modeb`, see `mamey/strain_modeb.py`). Interpretation remains pending.
6. **Figures and handoff** run supported post-seal commands and record their outputs before
   progress changes.

Every station transition requires a successful local receipt. "Load last validated run"
recomputes the stored manifest hash and keeps downstream stations locked on mismatch. Operator
progress and evidence/admission state are shown in separate fields. Lab Quest cannot issue
`OWNER_REVIEWED` or `RELEASE_APPROVED` states.

## Provenance and claim boundary

Every screen displays the configured code-tier root, bundle and engine versions, binding hash,
input ZIP hash, workflow state, evidence state, package-manifest hash, run mode, release class,
and evidence date when a package is bound. A package `PASS` is a current mechanical validation
result; it does not establish scientific completeness or biological interpretation.

Every individual locus is displayed in this required order:

`strain / full node-or-contig / region / BGC alias`

Missing or shortened identity fails closed (`mamey.exact_identity.ExactLocusIdentityError`).
`mamey/strain_modeb.py`'s S3/S4/S7 surfaces use this same helper, so a strain-level Mode B card and
the Lab Quest interface never disagree about how one BGC is identified. The interface makes no
compound identity, metabolite-production, activity, causal-linkage, biological-absence,
owner-acceptance, integration, release, or publication claim.

## Safety, accessibility, and formal use

- Upload names, strain identifiers, paths, and metadata are validated before use. All UI inputs
  and receipts stay below the chosen project root.
- User input is rendered with native Streamlit components; the interface uses no remote fonts,
  tracking, remote images, or unsafe HTML interpolation.
- Low-motion mode is enforced: the interface contains no animation-dependent status. Native
  controls support keyboard navigation, and progress is spelled out in text rather than colour
  alone.
- Arcade review and neutral scientific-review themes are available. Scientific review offers a
  local Markdown workflow record without the Lab Quest persona or emoji; it contains provenance
  and typed states only, not a scientific result or formal publication export.
- Figures displayed through future extensions must provide text alternatives
  (`show_figure_with_alt_text`); rendering a figure is never publication approval.

## Historical material

Historical workspace applications, old smoke packages, phosphonate prototypes, and strain prose
are dated prototype material only. They are not imported, discovered, or displayed as current
authority. Any current prose must be regenerated from governed evidence with exact identities,
typed holds, current claim ceilings, and owner review.

## Portfolio, privacy, and catalog layer

`mamey/portfolio_config.py` binds a project root to a `mamey/project_registry.py` registry
(privacy tiers, strain records, assay evidence — see that module's own docstring); `docs/PROJECT_REGISTRY.md`-style detail lives in `mamey/project_registry.py`'s module docstring itself. `mamey/project_catalog.py` is the hash-bound, portable package catalog plus the private (non-public, non-redacted)
project handoff — `export_private_project_handoff`/`import_private_project_handoff` carry a bound
portfolio along automatically when one is present (`lab_quest_outputs/portfolio_binding.json`),
verified hash-for-hash on both ends. Operator front doors: `tools/validate_portfolio_config.py`
and `tools/project_catalog.py`.

This layer deliberately does **not** reimplement privacy from scratch: it consumes
`mamey/project_registry.py` as the single producer of a package's `privacy_tier` /
`privacy_assignment_state` fields (see `mamey/models.py`), rather than adding a second or third
privacy mechanism. `mamey/lab_quest.py`'s `PackageSnapshot` and `mamey/lab_quest_app.py`'s package
station display and register a catalog entry for every validated package.

**Still out of this candidate's grant:** the profile-backed extraction-admission layer
(`PortfolioPrivacyContext` and friends, from the CODEX_391_PROFILE_BACKED_EXTRACTION_ADMISSION
lineage) — that lineage's own decision record lists every other CODEX_391 Lab Quest candidate as a
prerequisite and defers to a separate owner decision; it is not part of this pass.
