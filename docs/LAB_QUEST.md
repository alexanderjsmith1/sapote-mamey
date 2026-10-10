# Lab Quest: governed optional local interface

Lab Quest is a local accessibility and navigation layer over one explicitly configured portable
Mamey code tier. It is not a second biological engine, a workspace-discovery tool, or scientific
authority.

**Status (v9.7.444): an optional add-on.** Lab Quest is not part of the analysis methods, so it moved out of the
core `mamey` package into `sapote_addons/lab_quest/`: the package `sapote_addons/lab_quest/sapote_lab_quest/`
holds the library, the workflow registry and the Streamlit app. Install it from the bundle root with
`pip install ./sapote_addons/lab_quest` (needs streamlit), or offline with
`SAPOTE_INSTALL_LAB_QUEST=1 bash bundle_support/install_sapote_addons.sh` when a streamlit wheel is in the add-on pool.
The core CLI registers `python mamey_run.py lab-quest ...` only when the add-on is installed; otherwise the command is
absent from `--help` and typing it prints how to install it. The shared exact-locus contract
(`mamey/exact_identity.py`) and the portfolio/privacy/catalog layer (`mamey/portfolio_config.py`,
`mamey/project_catalog.py`, which write `lab_quest_outputs/`) stay in core.

## Install and launch

Install the optional interface dependencies from the extracted bundle, then bind the exact code
tier and expected versions deliberately:

```bash
python -m pip install ./sapote_addons/lab_quest   # install the add-on in the engine venv
python mamey_run.py lab-quest \
  --project-root /path/to/project \
  --code-tier /path/to/extracted/sapote-mamey \
  --expect-bundle-version "<expected bundle version>" \
  --expect-engine-version "<expected engine version>" \
  --headless
```

The launcher refuses to start unless both `--project-root` and `--code-tier` are explicitly
supplied. It then requires the configured code tier to contain `mamey_run.py`, `pyproject.toml`,
and `mamey/__init__.py`, with bundle and engine versions that each agree with their corresponding metadata and the
expected values. Neither the command-line launcher nor the app accepts an unset project-root
binding or falls back to the launch directory. The launcher uses no glob, "newest version," or
personal-workspace search. The local server binds to `127.0.0.1` and disables Streamlit telemetry.

Use `--verify-only` with the same required bindings after making the add-on importable to validate the portable source and write an
engine-binding receipt without launching the interface. The verification branch does not import Streamlit, but normal pip installation of the add-on declares `streamlit>=1.30` and may install it. This is a local
provenance check only, not a package, scientific, owner-review, release, or publication approval.

Both verification and launch can create the configured project directory and overwrite
`<project-root>/lab_quest_outputs/engine_binding.json`. The receipt is written before the launcher
checks Streamlit availability, so a failed UI launch can still leave a binding receipt. Preserve an
existing receipt or use a new project root when its earlier provenance must remain unchanged.
The binding hash covers `mamey/__init__.py`, `mamey_run.py` and `pyproject.toml`; it is not a hash
of all engine modules, installed dependencies or governed datasets.

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
`mamey/strain_modeb.py` and the Lab Quest interface use the shared identity helpers.
These provide a common display format; compare the bound run and source inputs as well. The interface makes no
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

The portfolio configuration consumes `mamey/project_registry.py` for declared project privacy, genome and assay metadata. This is distinct from the engine's extraction privacy assignment: in this .447 source, `--privacy-profile` drives binary package release and BGC `privacy_tier`/`privacy_assignment_state`; `--project-registry` records project fields and assay context but does not drive those release fields. Supplying both flags in one extraction is refused with `PRIVACY_AUTHORITY_CONFLICT`. Do not treat a recorded project tier as an enforced export classification.

Historical rebase comments saying `privacy_profile.py`/`evidence_registry.py` never landed are stale for this source, where those modules and intake flags exist. Use the actual CLI derivation and selected registry schema rather than that historical comment as authority. The interface's package snapshot and catalog read recorded package privacy fields; they do not reconcile these separate authorities.

For standalone catalog commands, exact writes, manifest-hash scope and private archive recovery, use the [project catalog guide](PROJECT_CATALOG.md).

**Historical integration prerequisite:** the earlier profile-backed extraction-admission
decision for `PortfolioPrivacyContext` listed companion components as prerequisites
and required separate review. That record does not establish that those dependencies
are integrated in the selected bundle. Confirm the actual code and versioned
prerequisite receipts before using that workflow. This interface guide does not
resolve the recorded integration hold.
