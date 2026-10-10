# Portable strain privacy and evidence registry

Sapote-Mamey can be used with a collection in which genome availability, bioassay scope, fractionation depth, and release status vary by strain. These facts remain separate. A genome does not imply a screen, a screen does not imply a fraction, a fraction does not imply chemical identity, and strain-level evidence does not establish a BGC-level causal link.

## Privacy profiles

Copy [`examples/privacy/strain_privacy_profile.example.json`](../examples/privacy/strain_privacy_profile.example.json) and replace the generic names with your own opaque strain IDs and access tiers. The profile supports any number of named tiers. Only tiers with `"public_export": true` map to the existing `PUBLIC` package release class. Every other tier maps to `PRIVATE` at that package boundary.

The default tier must be non-public. A strain omitted from the exact assignment list remains non-public instead of inheriting a decision from an ID prefix or filename. A `--release PUBLIC` request cannot bypass the profile: a nonpublic tier remains PRIVATE and records `public_override_refused_by_profile`; this resolution is not necessarily a failing run. Inspect the actual package assignment state and release field. Use `--release PRIVATE` only to make an already more restrictive export.

Run a Mamey extraction with a profile using:

```bash
python mamey_run.py run --strain isolate-001 --input-zip isolate-001.zip \
  --privacy-profile privacy/strain_privacy_profile.json
```

The generated package keeps its established binary `release` field for existing consumers and adds the profile's named privacy tier and assignment state per BGC. A profile is operator policy, not scientific evidence and not publication approval.

## Heterogeneous evidence registry

Copy [`examples/privacy/strain_evidence_registry.example.tsv`](../examples/privacy/strain_evidence_registry.example.tsv). The registry preserves a minimal lineage: a `material` row declares an extract or fraction, `parent_material_id` points to the material it came from, and one `assay` row names the panel and target tested against that exact material. This supports unequal pathogen panels and multiple flash/HPLC branch depths without collapsing them into a strain-level positive.

Each material retains its actual level: `crude_extract`, `flash_fraction`, or `hplc_fraction`. A fraction must name a non-root parent. An assay must point to an existing material from the same strain and carry its actual `replicate_state`; `SINGLETON` is not silently converted to replication. `RESULTS_BOUND` means only that a result record has been bound; it does not make a result potent, purified, or genetically attributable.

Validate both registry files before relying on them:

```bash
python tools/validate_portfolio_registry.py \
  --privacy-profile privacy/strain_privacy_profile.json \
  --evidence-registry evidence/strain_evidence_registry.tsv
```

The validator checks required nonblank headers/values, unique record/material IDs, evidence/material/assay-state vocabularies, parent existence, fraction non-root parents, assay-to-material strain agreement, and profile-tier agreement. It currently does not detect material-parent cycles or cross-strain material parents, enforce a replicate-state vocabulary, or open/hash each `source_locator`. A PASS is therefore a limited metadata check, not complete lineage or result-source verification. It prints an availability summary only. It does not import assay measurements into a genome run, score a BGC, or produce a scientific conclusion.

For a recorded result, separately verify the source bytes, material-parent strain consistency, cycle-free lineage and exact replicate meaning before scientific use. Preserve unresolved source/lineage states rather than inferring them from RESULTS_BOUND.

A `--project-registry` input is a separate registry format. Current extraction refuses pairing it with `--privacy-profile`; the registry records policy/context while the profile owns named-tier/binary release resolution. See [the project catalog guide](PROJECT_CATALOG.md) for that separate workflow.

## Export boundary

This registry is an operator-controlled input. A public cut must still pass the release manifest, denylist, redaction, and leak-audit gates. Privacy assignment, evidence admission, biological validation, owner acceptance, and publication release remain independent decisions.

## Project-registry validation and receipt limits

The two portfolio validators accept different inputs. `tools/validate_portfolio_registry.py` takes the extraction privacy-profile JSON and evidence TSV shown above; selected policy/evidence validation errors print `FAIL` to stderr and exit 2. `tools/validate_portfolio_config.py` takes a project root and pointer-config JSON naming a `sapote_project_registry_v1` registry. Its successful stdout is the binding JSON; failures can propagate as tracebacks. Capture stdout, stderr and exit status for either route, and keep those input schemas separate (`tools/validate_portfolio_registry.py:14–25`; `tools/validate_portfolio_config.py:27–38`).

The project registry rejects duplicate tier/strain/assay IDs, unknown declared tiers and assays referring to undeclared strains. It accepts an empty strain/assay collection if at least one tier exists. Use actual JSON integers for nonnegative `audience_rank` and `replicate_count`, strings for IDs, and a list of nonblank strings for `target_ids`: current coercion can turn fractional ranks into truncated integers, booleans into counts and dictionary keys into target IDs. Loader success does not prove those inputs had their intended types (`mamey/project_registry.py:104–129,179–272`).

In this project schema, source locators, source SHA-256 text and parent-material IDs are recorded declarations. The loader does not open/hash each cited source, validate SHA-256 syntax or resolve a cycle-free material graph. That differs from the separate evidence-TSV validator's limited parent-existence checks. Verify source bytes and lineage independently before relying on a recorded result.

`assay_data_state: AVAILABLE` means at least one assay record exists, including a record marked `NOT_TESTED`, `NOT_RETURNED` or `UNBOUND`. Read `result_state_counts` and exact material/condition/source fields alongside it. The counts are declared records and distinct declared target labels, not independent replicates, tested-target coverage, positive outcomes or genomic causal evidence (`mamey/project_registry.py:335–354`; `mamey/portfolio_config.py:96–117`).

A project-registry export decision compares declared audience ranks; it does not perform export or approve disclosure. Unknown strains are held, and absence of an explicit public-export tier maps to PRIVATE. `write_strain_registry_surfaces` writes `project_registry_snapshot.json` followed by `bioassay_scope.tsv` directly; it can replace prior files and a later failure can leave a partial pair. Preserve existing outputs and use a fresh authorized output directory. This helper itself is not a sealed-package transaction (`mamey/project_registry.py:280–333,398–433`).
